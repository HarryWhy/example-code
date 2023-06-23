import asyncio
import collections

import aiohttp
from aiohttp import web
import tqdm

from flags2_common import main, HTTPStatus,Result,save_flag

DEFAULT_CONCURR_REQ = 5
MAX_CONCUR_REQ = 1000


class FetchError(Exception):
    def __init__(self,country_code):
        self.country_code = country_code


async def as_request(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            print('resp status and type:',resp.status,type(resp))
            # print(awiat resp.text())
            if resp.status ==200:
                print('status 200')
                image = await resp.read()
                return image
            elif resp.status == 404:
                print('status 404')
                raise web.HTTPNotFound()
            else:
                print('other status')
                raise aiohttp.HttpProcessingError(
                    code = resp.status,message = resp.reason,headers =resp.headers)



async def get_flag(base_url,cc):
    print(cc,'is request')
    url ='{}/{cc}/{cc}.gif'.format(base_url,cc=cc.lower())
    print(url,'is url')
    image = await as_request(url)
    print('request is running in async')
    return image
        

async def download_one(cc,base_url,semaphore,verbose):
    try:
        async with semaphore:
            print('semaphore is protecting')
            image = await get_flag(base_url,cc)
            print(image)
    except web.HTTPNotFound:
        print('exception #1 is raised')
        status =HTTPStatus.not_found
        msg ='not found'
    except Exception as exc:
        print('exception #2 is raised',exc)
        raise FetchError(cc) from exc
    else:
        print('image is saving')
        save_flag(image,cc.lower()+'.gif')
        status =HTTPStatus.ok
        msg ='OK'

    if verbose and msg:
        print(cc,msg)

    return Result(status,cc)


async def downloader_coro(cc_list,base_url,verbose,concur_req):
    counter = collections.Counter()
    semaphore = asyncio.Semaphore(concur_req)
    print('semaphore',concur_req,'verbose',verbose)
    to_do = [download_one(cc,base_url ,semaphore,verbose) for cc in sorted(cc_list)]

    to_do_iter = asyncio.as_completed(to_do)
    if not verbose:
        to_do_iter = tqdm.tqdm(to_do_iter,total=len(cc_list))

    for future in to_do_iter:
        try:
            res =await future
        except FetchError as exc:
            country_code =exc.country_code
            try:
                error_msg =exc.__cause__.args[0]
            except IndexErro:
                error_msg =exc.__cause__.__class__.__name__
            if verbose and error_msg:
                msg ='*** Error for {}:{}'
                print(msg.format(country_code,error_msg))
            status = HTTPStatus.error
        else:
            status = res.status
        counter[status]+=1
    
    return counter

# def process_args(default_concur_req):
#     print('process_args')
#     server_options = ', '.join(sorted(SERVERS))
#     parser = argparse.ArgumentParser(description = 'Download flags for country codes.'
#                                      'Default: top 20 countries by population.')
#     parser.add_argument('cc',metavar='CC',nargs ='*',help ='country code or 1st letter(eg. B for BA...BZ)')
#     parser.add_argument('-a','--all',action='store_true',help='get all available flags (AD to ZW)')
#     parser.add_argument('-e','--every',action='store_true',help='get flags for every possible code (AA...ZZ)')
#     parser.add_argument('-l','--limit',metavar='N',type=int,help='limit to N first codes',default= sys.maxsize)
#     parser.add_argument('-m','--max_req',metavar ='CONCURRENT', type = int,default =default_concur_req,help='maximum concurrent requests(default={})'.format(default_concur_req))
#     parser.add_argument('-s','--server',metavar ='LABEL',default = DEFAULT_SERVER,help='Server to hit; one of {} (default={})'.format(server_options,DEFAULT_SERVER))
#     parser.add_argument('-v','--verbose',action='store_true',help='output detailed progress info')
#     args = parser.parse_args()
#     if args.max_req < 1:
#         print('*** Usage error : --max_req CONCURRENT must be >=1')
#         parser.print_usage()
#         sys.exit(1)
#     if args.limit < 1:
#         print('*** Usage error : --limit N must be >=1')
#         parser.print_usage()
#         sys.exit(1)
#     args.server = args.server.upper()
#     if args.server not in SERVERS:
#         print('*** Usage error : --server LABEL must be one of',server_options)
#         parser.print_usage()
#         sys.exit(1)
#     try:
#         cc_list = expand_cc_args(args.every,args.all,args.cc,args.limit)
#     except ValueError as exc:
#         print(exc.args[0])
#         parser.print_usage()
#         sys.exit(1)
    
#     if not cc_list:
#         cc_list = sorted(POP20_CC)
#     return args,cc_list
    

def download_many(cc_list,base_url,verbose,concur_req):
    loop = asyncio.get_event_loop()
    coro = downloader_coro(cc_list,base_url,verbose,concur_req)
    counts =loop.run_until_complete(coro)
    loop.close()

    return counts

# def main(download_many,default_concur_req,max_concur_req):
#     print('main')
#     args,cc_list = process_args(default_concur_req)
#     actual_req = min(args.max_req,max_concur_req,len(cc_list))
#     initial_report(cc_list,actual_req,args.server)
#     base_url =SERVERS[args.server]
#     t0 =time.time()
#     counter =download_many(cc_list,base_url,args.verbose,actual_req)
#     assert sum(counter.values()) == len(cc_list),'some downloads are unaccounted for'
#     finial_report(cc_list,counter,t0)


if __name__ == '__main__':
    main(download_many, DEFAULT_CONCURR_REQ,MAX_CONCUR_REQ)
