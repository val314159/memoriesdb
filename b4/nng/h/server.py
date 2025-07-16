from collections import defaultdict
import asyncio
import websockets


# channels
C = defaultdict(list)


async def main():

    async def pub_sub_server(ws):

        try:

            # get list of channel names
            mychannels = (ws.request.path+',0').split('ch=')[-1].split(',')
        
            # subscribe
            print("+SUB", mychannels)
            for ch in mychannels:
                C[ch].append(ws)
                pass
        
            # listen/publish loop
            async for message in ws:

                if state == 0:
                    # save first message
                    
                    state, head, body = 0, message, None

                    ch, xid = head.split(':')
                    
                elif state == 1:
                    # process both messages
                    
                    state, body = 0, message

                    if ch.startswith('ack'):
                        # it's an ack: we should delete it out of the queue
                        # except we're not really doing a queue at all so we ignore
                        continue

                    for w in C[ch]:                        
                        w.send(head)
                        w.send(body)
                        pass
                        
                  else: pass # end for w in C[ch]:
                    
                else:
                    raise Exception('bad state')
                
        except Exception:

            # is there a way to see if this is closed already?
            await ws.close()
            raise
            
        finally:

            # unsubscribe
            print("-UNS", mychannels)
            for ch in mychannels:
                if len(C[ch]) < 2: del C[ch]
                else             :     C[ch].remove(ws)
            else: pass
            pass
        pass

    
    async with websockets.serve(pub_sub_server, '', 8765):
        await asyncio.Future()  # Run forever



if __name__ == "__main__":
    asyncio.run(main())

