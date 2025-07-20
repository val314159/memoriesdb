const print=console.log, loads=JSON.parse, dumps=JSON.stringify
print("// app.js //")
const CH         = 'llm',
      CH_IN      = CH + '-in',
      CH_OUT     = CH + '-out',
      WS_BASE    = 'ws://localhost:5002/ws?c=',
      WS_TIMEOUT = 5 * 1000,
      WS_TIMEOUT2= 15 * 1000
class WsApp {
    constructor(){
	this.uuid    = 'TEST'
	this.session = 'LAST'
    }
    ondata(data){
	print("ONDATA", dumps(data))
	const method = data['method'],
	      params = data['params']
	if(method=="initialize"){
	    print("WE ARE INITIALIZING DO WE HAVE A SESSION ID?")
	    this.uuid    = params['uuid']
	    this.session = params['session']
	    print(this.uuid)
	    print(this.session)
	}
	this._ondata(data)
    }
    pub(content, role, channel){
	this.ws.send( channel ||= CH_IN )
	this.ws.send( dumps( { method: 'pub',
			       params: { channel:      channel,
					 role   :      role || 'user',
					 content:      content,
					 uuid   : this.uuid,
					 session: this.session } } ) )
    }
    resetInactivityTimeout(){
	if (this.inactivityTimeout)
	    clearTimeout(this.inactivityTimeout)
	this.inactiveTimeout = setTimeout(()=>{
	    print("INACTIVE TIMEOUT, just reset the timer...", WS_TIMEOUT2)
	    this.resetInactivityTimeout()
	}, WS_TIMEOUT2)
    }
    resetConnectionTimeout(){
	this.connectionTimeout = setTimeout(()=>{
	    print("CONNECT TIMEOUT, let's retry")
	    this.connect()
	}, WS_TIMEOUT)
    }
    connect(){
	const uri = WS_BASE + CH_OUT
	print(`Connecting WebSocket ${uri}...`)
	this.ws = new WebSocket(uri)
	this.resetConnectionTimeout()
	this.ws.onopen    =e=>{	
	    print("WEBSOCKET OPEN", e)
	    //this.resetInactivityTimeout()
	    clearTimeout(this.connectionTimeout)
	}
	this.ws.onmessage =e=>{	
	    print("WEBSOCKET MESG", e)
	    //this.resetInactivityTimeout()
	    this.ondata(loads(e.data))
	}
	this.ws. onclose  =e=>{
	    print("WEBSOCKET CLOS", e)
	    //setTimeout(this.connect, WS_TIMEOUT)
	}
	this.ws.onerror   =e=>{
	    print("WEBSOCKET ERRR", e)
	    //setTimeout(this.connect, WS_TIMEOUT)
	}
	return this
    }
}
const app = (new class App extends WsApp {
    _ondata(params){
	print("DATA", dumps(params))
    }
}).connect()
const  sys = (content, channel)=> app.pub(content, 'system')
const user = (content, channel)=> app.pub(content)
