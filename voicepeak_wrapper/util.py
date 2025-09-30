import asyncio

def say_text_sync(client, line, wav_path, voice):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.say_text(line, output_path=wav_path, narrator=voice))
    loop.close()
