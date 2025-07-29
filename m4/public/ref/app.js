const loads=JSON.parse, dumps=JSON.stringify, print=console.log
const CH         = 'llm6',
      CH_OUT     = CH + '-out',
      CH_IN      = CH + '-in',
      DB_IN      =    'db-in',
      WS_BASE    = `ws://${location.host}/ws?c=`,
      WS_TIMEOUT =  5 * 1000,
      WS_TIMEOUT2= 15 * 1000
class WsApp {
    constructor(){ this.uuid = this.session = this.lastId = 0 }
    pub(content, role, channel){
	this.ws.send( channel ||= CH_IN )
	print       ( dumps( { method: 'pub',
			       params: { channel:      channel,
					 role   :      role || 'user',
					 content:      content,
					 uuid   : this.uuid,
					 session: this.session } } ) )
	this.ws.send( dumps( { method: 'pub',
			       params: { channel:      channel,
					 role   :      role || 'user',
					 content:      content,
					 uuid   : this.uuid,
					 session: this.session } } ) ) }
    resetInactivityTimeout(){
	if (this.inactivityTimeout)
	    clearTimeout(this.inactivityTimeout)
	this.inactiveTimeout = setTimeout(()=>{
	    print("INACTIVE TIMEOUT, just reset the timer...", WS_TIMEOUT2)
	    this.resetInactivityTimeout()
	}, WS_TIMEOUT2) }
    resetConnectionTimeout(){
	this.connectionTimeout = setTimeout(()=>{
	    print("CONNECT TIMEOUT, let's retry")
	    this.connect()
	}, WS_TIMEOUT) }
    connect(){
	const uri = WS_BASE + CH_OUT + '&c=db-out'
	print(`Connecting WebSocket ${uri}...`)
	this.ws = new WebSocket(uri)
	this.resetConnectionTimeout()
	this.ws.onopen    =e=>{	
	    print("WEBSOCKET OPEN", e)
	    //this.resetInactivityTimeout()
	    clearTimeout(this.connectionTimeout) }
	this.ws.onmessage =e=>{	
	    const data = loads(e.data)
	    const method = data.method,
		  params = data.params
	    if (method=="initialize")
		this.on_initialize(params)
	    else if (method=="pub")
		this.on_pub(params)
	    else
		alert("BAD METHOD: "+ method)}
	this.ws. onclose  =e=>{
	    print("WEBSOCKET CLOS", e)
	    //setTimeout(this.connect, WS_TIMEOUT)
	}
	this.ws.onerror   =e=>{
	    print("WEBSOCKET ERRR", e)
	    //setTimeout(this.connect, WS_TIMEOUT)
	}
	return this}}
