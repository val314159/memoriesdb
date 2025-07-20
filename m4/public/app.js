const print=console.log, loads=JSON.parse, dumps=JSON.stringify
print("// app.js //")
const CH         = 'llm',
      CH_IN      = CH + '-in',
      CH_OUT     = CH + '-out',
      WS_BASE    = 'ws://localhost:5002/ws',
      WS_ARGS    = '?c=' + CH_OUT,
      WS_TIMEOUT = 5 * 1000,
      _ = new class App {
	  constructor(){
	      const _ = this
	      _.uuid    = '00000000-0000-0000-0000-000000000000'
	      _.session = '11111111-1111-1111-1111-111111111111'
	  }
	  ondata(data){
	      print("DATA", data['method'], dumps(data['params']))
	  }
	  pub(content, role, channel){
	      role    ||= 'user'
	      channel ||= CH_OUT
	      const uuid    = '00000000-0000-0000-0000-000000000000',
		    session = '11111111-1111-1111-1111-111111111111',
		    method = 'pub',
		    params = { uuid, role, channel, content },
		    mesg   = { method, params }
	      _.ws.send(dumps(mesg))
	  }
	  connect(){
	      const uri = WS_BASE + WS_ARGS
	      print(`Connecting WebSocket ${uri}...`)
	      _.ws = new WebSocket(uri)
	      const connectTimeout = setTimeout(()=>{
		  print("WEBSOCKET TIMEOUT, let's retry")
		  _.connect()
	      }, WS_TIMEOUT)
	      _.ws.onopen=e=>{
		  //print("WEBSOCKET OPEN1", e)	
		  clearTimeout(connectTimeout)
		  print("WEBSOCKET OPEN2", e)	
	      }
	      _.ws.onmessage=e=>{
		  print("WEBSOCKET MESG ", e)	
		  _.ondata(loads(e.data))
	      }
	      _.ws. onclose=e=>{
		  print("WEBSOCKET CLOSE", e)	
		  setTimeout(_.connect, WS_TIMEOUT)
	      }
	      _.ws.onerror=e=>{
		  print("WEBSOCKET ERROR", e)
		  _.connect()
	      }
	      return _
	  }
      }, app = _.connect()
const user=(content, channel)=>pub(content)
const  sys=(content, channel)=>pub(content, 'system')
