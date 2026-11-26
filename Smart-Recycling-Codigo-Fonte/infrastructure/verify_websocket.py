import asyncio,base64,json,pathlib,subprocess
access=json.loads(pathlib.Path('/opt/smart-recycling/access.json').read_text())
auth='Basic '+base64.b64encode((access['username']+':'+access['password']).encode()).decode()
script='''import asyncio,websockets
async def main():
    async with websockets.connect("wss://mrvbot.com/smart_recycling/ws",additional_headers={"Authorization":AUTH}) as ws:
        await ws.send("ping")
        await ws.ping()
        print("PASS: WebSocket HTTPS autenticado conectado")
asyncio.run(main())
'''.replace('AUTH',repr(auth))
subprocess.run(['docker','exec','-i','smart-recycling-api-1','python','-'],input=script.encode(),check=True)
