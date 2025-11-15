"""
Example PTZ Camera + OBS + HomeAssistant Automation Bridge
----------------------------------------------------------
This is a sanitized template version of a personal project.
All IPs, tokens, scenes, presets, and entity IDs must be replaced
with values appropriate for your own environment.

This code is not intended for production use.

Camera Controller V0.1
No UI yet everything is hardcoded
"""

import requests
import websockets
import json
import asyncio
import simpleobsws

# Fill with actual values
HOMEASSISTANT_TOKEN = ""
HOMEASSISTANT_PORT = 8123
HOMEASSISTANT_IP = "homeassistant.local"
CAMERA_20X_IP = "cam20x.local"
CAMERA_30X_IP = "cam30x.local"
OBS_IP = "obs.local"
OBS_PORT = 4455


class response:
    def __init__(self, ok: bool, data: str = None):
        self.ok = ok
        self.data = data

    def json(self):
        return json.loads(self.data)


class HomeAssistantIO:
    def __init__(self, ip: str, port: int, token: str) -> None:
        self.ip = ip
        self.port = port
        self.token = token
        self.ws = None
        self.messageCount = 0

        self.subscribed_entities = []

    async def connect(self) -> response:
        print("HA Connecting")
        try:
            self.ws = await websockets.connect(
                f"ws://{self.ip}:{self.port}/api/websocket"
            )
            status = await self.receive()
        except Exception as e:
            return response(False, e)

        auth_message = {"type": "auth", "access_token": self.token}

        status = await self.send(auth_message)
        await asyncio.sleep(0.1)
        status = await self.receive()
        print(status.data)
        if status.ok:
            if status.json()["type"] != "auth_ok":
                return status
            else:
                await self.onConnect()
                return response(True)
        else:
            return status

    async def receive(self) -> response:
        try:
            data = await self.ws.recv()

        except Exception as e:
            return response(False, e)
        return response(True, data)

    async def send(self, data: str) -> response:
        self.messageCount += 1
        try:
            await self.ws.send(json.dumps(data))

        except Exception as e:
            return response(False, e)
        return response(True)

    async def sub_to_entity(self, entity: str, type: str = "input_button") -> response:
        message = {
            "id": self.messageCount,
            "type": "subscribe_trigger",
            "trigger": {
                "platform": "state",
                "entity_id": f"{type}.{entity}",
                "not_from": "null",
            },
        }
        print(message)
        status = await self.send(message)
        status = await self.receive()
        while status.json()["type"] != "result":
            status = await self.receive()
        print(status.data)
        if status.ok:
            if not status.json()["success"]:
                print(status.json()["success"])
                return response(False, status.data)
            else:
                self.subscribed_entities.append(
                    {"type": type, "entity": entity, "id": self.messageCount - 1}
                )
                return response(True)

        else:
            return status

    async def unsub_from_entity(self, entity: str, type: str = "input_button") -> response:
        for n, message in enumerate(self.subscribed_entities):
            if (message["entity"] == entity) and (message["type"] == type):
                index = n
                break
        message = {
            "id": self.messageCount,
            "type": "unsubscribe_events",
            "subscription": self.subscribed_entities[index]["id"],
        }
        status = await self.send(message)
        if status.ok:
            if status.json()["success"] != "true":
                return status
            else:
                self.subscribed_entities.pop(index)
                return response(True)

        else:
            return status


class OBSIO:
    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.ws = simpleobsws.WebSocketClient(url=f"ws://{ip}:{port}")

    async def connect(self) -> response:
        print("Connecting to OBS")
        self.ws = simpleobsws.WebSocketClient(
            url=f"ws://{self.ip}:{self.port}")
        try:
            await self.ws.connect()
            await self.ws.wait_until_identified()

        except Exception as e:
            print(e)
            return response(False, e)
        print("Connected")
        return response(True)

    async def send(self, request, data={}) -> response:
        error = False
        req = simpleobsws.Request(request, data)
        try:
            ret = await self.ws.call(req)
        except Exception as e:
            print(False, e)
            error = True
        if not error:
            if not ret.ok():
                error = True
                print(False, ret.responseData)
        if error:
            print("Reconnecting")
            obsStatus = await self.connect()
            print(obsStatus.data)
            return await self.send(request, data)

        return response(True, ret.responseData)


class PTZCamIO:
    def __init__(self, ip: str, presets: dict):
        self.ip = ip
        self.presets = presets

    def getPresets(self) -> list:
        return list(self.presets.keys())

    def recallPreset(self, preset: str) -> response:
        if preset not in self.getPresets():
            return response(False, "Not existing preset")
        try:
            status = requests.get(
                f"http://{self.ip}/cgi-bin/ptzctrl.cgi?ptzcmd&poscall&{self.presets[preset]}"
            )
        except Exception as e:
            return response(False, e)
        if not status.ok:
            return response(False, "Failed to Communicate with camera")
        return response(True, status.status_code)

    def directCall(self, url: str, method: str = "GET") -> response:
        try:
            status = requests.request(method, f"http://{self.ip}{url}")
        except Exception as e:
            return response(False, e)
        if not status.ok:
            return response(False, "Failed to Communicate with camera")
        return response(True, status.status_code)

# Fill with actual preset names
cam_20x_presets = {
    "preset_1": 0,
    "preset_2": 1,
    "preset_3": 2,
    "preset_4": 3,
    "preset_5": 4,
    "preset_6": 5,
    "preset_7": 6,
    "preset_8": 7,
}

cam_30x_presets = {
    "preset_1": 0,
    "preset_2": 1,
    "preset_3": 2,
    "preset_4": 3,
    "preset_5": 4,
    "preset_6": 5,
    "preset_7": 6,
    "preset_8": 7,
}

# Can modify special buttons as needed
special_buttons = {
    "start_stop_stream": {
        "type": "input_boolean",
        "start": [
            {"platform": "OBS", "request": "StartStream", "data": {}},
            {"platform": "OBS", "request": "StartRecord", "data": {}},
        ],
        "stop": [
            {"platform": "OBS", "request": "StopStream", "data": {}},
            {"platform": "OBS", "request": "StopRecord", "data": {}},
        ],
    },
    "restart_20x": {
        "type": "input_button",
        "trigger": [
            {
                "platform": "PTZ_20",
                "request": "POST",
                "data": "/cgi-bin/param.cgi?post_reboot",
            }
        ],
    },
    "restart_30x": {
        "type": "input_button",
        "trigger": [
            {
                "platform": "PTZ_30",
                "request": "POST",
                "data": "/cgi-bin/param.cgi?post_reboot",
            }
        ],
    },
    "BUTTON_NAME_HERE": {
        "type": "input_button",
        "trigger": [
            {
                "platform": "OBS",
                "request": "SetCurrentPreviewScene",
                "data": {"sceneName": "SCENE_NAME_HERE"},
            },
            {"platform": "OBS", "request": "TriggerStudioModeTransition", "data": {}},
        ],
    },
    "auto_stream": {
        "type": "input_boolean",
        "start": [
            {
                "platform": "PTZ_20",
                "request": "GET",
                "data": "/cgi-bin/ptzctrl.cgi?ptzcmd&poscall&3",
            },
            {
                "platform": "OBS",
                "request": "SetCurrentPreviewScene",
                "data": {"sceneName": "SCENE_NAME_HERE"},
            },
            {"platform": "OBS", "request": "TriggerStudioModeTransition", "data": {}},
            {"platform": "OBS", "request": "StartStream", "data": {}},
            {"platform": "OBS", "request": "StartRecord", "data": {}},
        ],
        "stop": [
            {"platform": "OBS", "request": "StopStream", "data": {}},
            {"platform": "OBS", "request": "StopRecord", "data": {}},
        ],
    },
}

# Create a List of all presets
unique_presets = []
for preset in cam_20x_presets.keys():
    if preset not in unique_presets:
        unique_presets.append(preset)

for preset in cam_30x_presets.keys():
    if preset not in unique_presets:
        unique_presets.append(preset)

cam_20x = PTZCamIO(CAMERA_20X_IP, cam_20x_presets)
cam_30x = PTZCamIO(CAMERA_30X_IP, cam_30x_presets)
obs = OBSIO(OBS_IP, OBS_PORT)
homeassistant = HomeAssistantIO(HOMEASSISTANT_IP, HOMEASSISTANT_PORT, HOMEASSISTANT_TOKEN)


async def process_special_cmd(cmd: str, state: str = "trigger") -> None:
    if cmd in special_buttons:
        for command in special_buttons[cmd][state]:
            if command["platform"] == "OBS":
                await obs.send(command["request"], command["data"])
            elif command["platform"] == "PTZ_30":
                cam_30x.directCall(command["data"], command["request"])
            elif command["platform"] == "PTZ_20":
                cam_20x.directCall(command["data"], command["request"])


async def sub_to_entities() -> None:
    for entity in unique_presets:
        data = await homeassistant.sub_to_entity(entity)
        await asyncio.sleep(0.1)
        if not data.ok:
            while not data.ok:
                data = await homeassistant.connect()
            await homeassistant.sub_to_entity(entity)
    for entry in special_buttons.keys():
        data = await homeassistant.sub_to_entity(entry, special_buttons[entry]["type"])
        await asyncio.sleep(0.1)
        if not data.ok:
            while not data.ok:
                data = await homeassistant.connect()
            await homeassistant.sub_to_entity(entity)


async def recall_preset(preset: str) -> response:
    if preset not in unique_presets:
        return response(False, "Invalid Preset")
    if (await obs.send("GetCurrentProgramScene")).data["sceneName"] == "30x":
        if preset in cam_20x_presets:
            cam_20x.recallPreset(preset)
            await obs.send("SetCurrentPreviewScene", {"sceneName": "20x"})
            await asyncio.sleep(3)
            await obs.send("TriggerStudioModeTransition")
            return response(True)
        else:
            cam_20x.recallPreset("front")
            await obs.send("SetCurrentPreviewScene", {"sceneName": "20x"})
            await asyncio.sleep(3)
            await obs.send("TriggerStudioModeTransition")
            cam_30x.recallPreset(preset)
            await obs.send("SetCurrentPreviewScene", {"sceneName": "30x"})
            await asyncio.sleep(3)
            await obs.send("TriggerStudioModeTransition")
            return response(True)
    else:
        if preset in cam_30x_presets:
            cam_30x.recallPreset(preset)
            await obs.send("SetCurrentPreviewScene", {"sceneName": "30x"})
            await asyncio.sleep(3)
            await obs.send("TriggerStudioModeTransition")
            return response(True)
        else:
            cam_30x.recallPreset("front")
            await obs.send("SetCurrentPreviewScene", {"sceneName": "30x"})
            await asyncio.sleep(3)
            await obs.send("TriggerStudioModeTransition")
            cam_20x.recallPreset(preset)
            await obs.send("SetCurrentPreviewScene", {"sceneName": "20x"})
            await asyncio.sleep(3)
            await obs.send("TriggerStudioModeTransition")
            return response(True)


async def receiver():
    while True:
        data = await homeassistant.receive()
        print(data.data)
        if data.ok == False:
            while data.ok == False:
                data = await homeassistant.connect()
            continue
        data = data.json()
        try:
            id = data["event"]["variables"]["trigger"]["entity_id"]
        except KeyError:
            print(f"Recv Error: {data}")
            continue
        if id.replace("input_button.", "") in unique_presets:
            await recall_preset(id.replace("input_button.", ""))
        elif id.split(".")[1] in special_buttons:
            if special_buttons[id.split(".")[1]]["type"] == id.split(".")[0]:
                if id.split(".")[0] == "input_boolean":
                    if data["event"]["variables"]["trigger"]["to_state"]["state"] == "on":
                        await process_special_cmd(id.split(".")[1], "start")
                    elif data["event"]["variables"]["trigger"]["to_state"]["state"] == "off":
                        await process_special_cmd(id.split(".")[1], "stop")
                else:
                    await process_special_cmd(id.split(".")[1])


async def init():
    homeassistant.onConnect = sub_to_entities
    haStatus = await homeassistant.connect()
    if not haStatus.ok:
        while not haStatus.ok:
            haStatus = await homeassistant.connect()

    obsStatus = await obs.connect()
    if not obsStatus.ok:
        while not obsStatus.ok:
            obsStatus = await obs.connect()

    await asyncio.sleep(5)
    await receiver()


loop = asyncio.get_event_loop()

loop.run_until_complete(init())
