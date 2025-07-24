const GEBI = x=>document.getElementById(x)
const app = (new class App extends WsApp {

    // MISC STATIC FUNCS

    displayText(s){
	print(s)
	GEBI("display").append(document.createTextNode(s))
	GEBI("display").append(document.createElement('br'))}

    top(){window.scrollTo(0, 0)}
    bot(){window.scrollTo(0, document.body.scrollHeight)}

    textNode(s){return document.createTextNode(s)}

    createElt(tag, html, id){
	if(!tag) return
	const elt = document.createElement(tag)
	elt.id = id
	elt.innerHTML = tag + ': ' + html
	return elt}

    // ACTION FUNCS

    listConvos(){
	this.displayText("LIST CONVOS: " + this.uuid)
	this.displayText("PUBLISH A MESSAGE TO A MICROSERVICE?")
	this.pub('listConvos', 'user', DB_IN)}

    newConvo(){
	this.displayText("NEW CONVO: " + this.uuid)
	this.displayText("PUBLISH A MESSAGE TO A MICROSERVICE?")
	this.pub('newConvo', 'user', DB_IN)}

    // prepend / apppend funcs

    prependMsg(role, content, id){
	const elt = this.createElt(role, content, id)
	if (elt) GEBI("display").prepend(elt)}

    appendMsg(role, content, id){
	const elt = this.createElt(role, content, id)
	if (elt) GEBI("display").append(elt)}
    
    appendMessage(params){
	const id = ++this.lastId
	this.appendMsg(params.role, params.content)
	this.appendMsg(  "thinking", '',  'thinking-'+id )
	this.appendMsg( "assistant", '', 'assistant-'+id )}

    appendThoughts(s){
	GEBI( "thinking-"+this.lastId).append(this.textNode(s))}

    appendContents(s){
	GEBI("assistant-"+this.lastId).append(this.textNode(s))}

    // callbacks
    
    on_initialize(params){ 
	const sp = new URLSearchParams(location.search)
	this.uuid    = sp.get('uuid'   ) || params['uuid']
	this.session = sp.get('session') || params['session']
	print(`INITIALIZE ${this.uuid} ${this.session}`)
	this.displayText(`INITIALIZE ${this.uuid} ${this.session}`)
	this.displayText("REQUEST HISTORY")
	this.pub('shortHistory', this.role, DB_IN)}
    
    on_pub(params){
	const channel = params.channel
	if      (channel.startsWith( 'db-')) _.on_db_message(params)
	else if (channel.startsWith('llm-')) _.on_llm_message(params)
	else                                print(">>PUB ERR", params)}

    on_db_message(params){
	print(">>DB", params)
	const fn = this['db_'+params.content]
	if(fn)
	    return fn.bind(this)(params)
	print('WARNING, NOT FOUND ' + dumps(params))}
    
    on_llm_message(params){
	print(">>LLM", params)
	var used = false;
	if(params.thinking){
	    used = true
	    this.llm_thinking(params)}
	if(params.content){
	    used = true
	    this.llm_speaking(params)}
	if(params.done){
	    used = true
	    this.llm_finished(params)}
	if(!used)
	    print('WARNING, NOT USED ' + dumps(params))
	return this.bot()}

    llm_thinking(params){
	this.appendThoughts(params.thinking)}

    llm_speaking(params){
	if(params.role=='user' || params.role=='system')
	    this.appendMessage(params)
	else if(params.role=='assistant')
	    this.appendContents(params.content)
	else
	    print("WARNING: WHATS THE ROLE HERE:", params)}

    llm_finished(params){
	GEBI("input").focus()}

    db_listConvos(params){
	used = true
	print("LIST", _.uuid, params.results)
	params.results.forEach(x=>{
	    print("X", x[0], " - ", x[1], '!')
	    const html = `<a href=.?session=${x[0]}>${x[1]}</a>`
	    GEBI("display").append(this.createElt("li", html))
	})}

    db_shortHistory(params){
	print("SHIST", _.uuid, params.results)
	var buffer = [], lastRole = ''
	params.results.forEach(x=>{
	    if(lastRole != x.role){
		this.prependMsg(lastRole, buffer.join(''))
		lastRole = x.role
		buffer.length = 0
	    }
	    buffer.unshift(x.content)
	})
	this.prependMsg(lastRole, buffer.join(''))}

    db_newConvo(params){
	print("NEWC", _.uuid, params.results)
    	setTimeout(()=>{
	    location = '.'
	    print("1REFRESH WITH THE NEW CONVO", _.uuid, params.results)
	    setTimeout(()=>{
		print("2REFRESH WITH THE NEW CONVO", _.uuid, params.results)
		location = '.'
		print("2REFRESH WITH THE NEW CONVO", _.uuid, params.results)
	    },1000)
	},1500)}

    keypress(e){
	if(e.key=='Enter' && !e.shiftKey && !e.ctrlKey){
	    event.preventDefault()
	    const input = e.target.value.trim()
	    e.target.value = ''
	    e.target.blur()
	    if(!input)return
	    console.log("INPUT "+input)
	    this.pub(input, this.role)
	    return this.bot()}}

    documentKeypress(event){
	if(event.key=='\\' && event.ctrlKey){
	    event.preventDefault()
	    print("^BRK", event.target)
	    GEBI("input").focus()
	    return this.bot()}}

    install(){
	const inputElt = GEBI("input")
	const role_Elt = GEBI("role")
	inputElt.addEventListener('keypress', e=>this.keypress(e))
	document.addEventListener('keypress', e=>this.documentKeypress(e))
	role_Elt.addEventListener('change',   e=>this.role=e.target.value)
	this.role = role_Elt.value
	return this}

} ).install().connect()
const sys  = (content, channel)=> app.pub(content, 'system')
const user = (content, channel)=> app.pub(content)
const ls   = ()=>app.listConvos()
const newc = ()=>app.newConvo()
const go_top=()=>app.top()
const go_bot=()=>app.bot()
window._ = app
