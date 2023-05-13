import aiohttp
import os
from aiohttp import web
import asyncio
import json
from taskmanager.task_manager import TaskManager

task_queue = None
CHECK_TASK_STATUS_SLEEP_DURATION = 5



# def init_func(argv):
#     app = web.Application()
#     app.router.add_get("/", handle)
#     return app


# app = web.Application()
# routes = web.RouteTableDef()
# tm = TaskManager()

# @routes.get('/')
# async def get_handler(request):
#     name = request.match_info.get('name', "Anonymous")
#     text = "Hello, " + name
#     return web.Response(text=text)

# @routes.post('/get_run_status')
# async def get_handler(request):
#     task_id = await request.post()
#     print("task_id:", task_id)
#     task_id = task_id['id']

# #сделать таймаут

#     response = {'id': task_id}
#     # while task_id in tm.task_dict:
#     while True:
#         async with tm.task_dict_lock:
#             # if task_id not in tm.task_dict:
#             #     response['Status'] = True
#             #     return web.json_response(response)
#             if tm.task_dict[task_id].run_status == True:
#                 # response['Status'] = False
#                 response['Message'] = tm.task_dict[task_id].errorMessage.decode()
#                 print("responce::::", response)
#                 del tm.task_dict[task_id]
#                 return web.json_response(response)

#         await asyncio.sleep(CHECK_TASK_STATUS_SLEEP_DURATION)

#     # return web.json_response({'id': task_id})

# @routes.put('/put')
# async def put_handler(request):
#     return web.Response()


# @routes.post('/post')
# async def post_handler(request):
#     task_cfg = await request.post()
#     print("CLIENT INFO:", request.remote)

#     new_task = await tm.add_task_to_queue(task_cfg)

#     response = 'Your task has been successfully added to queue\n'

#     if new_task.created_status is False:
#         response = {"Status": False, "Message": new_task.errorMessage}
#         print("CREATING TASK FAILED\n", new_task.errorMessage)
#         return web.json_response(response)


#     # while new_task.run_status is False:
#     #     await asyncio.sleep(3)


#     response = {"Status": True, "id": new_task.id}

#     return web.json_response(response)

# app.add_routes(routes)



async def background_tasks(app):
    app['task_checker'] = asyncio.create_task(tm.tasks_status_check(app))

    yield

    app['task_checker'].cancel()
    await app['task_checker']

# if __name__ == '__main__':
#     print("TaskManager created")
#     app.cleanup_ctx.append(background_tasks)
#     web.run_app(app, port=1488)

async def testhandle(request):
    return aiohttp.web.Response(text='Test handle')


async def websocket_handler(request):
    print('Websocket connection starting')
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    print('Websocket connection ready')

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            print("TYPE:", msg.json)
            task_cfg = msg.json()
            new_task = await tm.add_task_to_queue(task_cfg, ws)
            if new_task.created_status is False:
                response = new_task.errorMessage
            else:
                response = "Your task has been successfully added to queue\n"
            await new_task.web_socket.send_str(response)


    print('Websocket connection closed')
    return ws

tm = TaskManager()

def main():
    script_path = os.path.dirname(__file__)
    with open(script_path + '/../config.json') as config_file:
        URL = json.load(config_file)


    # loop = asyncio.get_event_loop()
    app = web.Application()
    app.router.add_route('GET', '/', testhandle)
    app.router.add_route('GET', '/ws', websocket_handler)
    app.cleanup_ctx.append(background_tasks)
    aiohttp.web.run_app(app, host='0.0.0.0', port=URL['port'])


if __name__ == '__main__':
    main()
    
