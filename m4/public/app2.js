const GEBI = x=>document.getElementById(x)
const app = (new class App extends WsApp {
    displayText(s){
	print(s)
	GEBI("display").appendChild(document.createTextNode(s))
	GEBI("display").appendChild(document.createElement('br'))}
    listConvos(){
	this.displayText("LIST CONVOS: " + this.uuid)
	this.displayText("PUBLISH A MESSAGE TO A MICROSERVICE?")
	this.pub('listConvos', 'user', DB_IN)}
    newConvo(){
	this.displayText("NEW CONVO: " + this.uuid)
	this.displayText("PUBLISH A MESSAGE TO A MICROSERVICE?")
	this.pub('newConvo', 'user', DB_IN)}
    top(){window.scrollTo(0, 0)}
    bot(){window.scrollTo(0, document.body.scrollHeight)}
      incrLastId(){return ++this.lastId}
        inputElt(){return GEBI(   "input-"+this.lastId)}
     thoughtsElt(){return GEBI("thinking-"+this.lastId)}
     contentsElt(){return GEBI( "content-"+this.lastId)}
    userInputElt(){return GEBI(   "input")}
      displayElt(){return GEBI(   "display")}
       textNode(s){return document.createTextNode(s)}
    appendThoughts(s){this.thoughtsElt().appendChild(this.textNode(s))}
    appendContents(s){this.contentsElt().appendChild(this.textNode(s))}
    appendMessage(params){
	const id = this.incrLastId()
	const message = this.createElt('message', `\
<message id="message-${id}">
  <div      id="input-${id}">${params.role}${id} // ${params.content}</div>
  <thinking id="thinking-${id}">thinking${id} // </thinking>
  <content  id="content-${id}">  content${id} // </content>
</message>`)
	this.displayElt().appendChild(message)}
    createElt(tag, html){
	const elt = document.createElement('message')
	elt.innerHTML = html
	return elt}
    _onpub(params){
	if(params.channel.startsWith('db-')){
	    print(">>DB", params)
	    return _._ondatabase(params)
	}else if(params.channel.startsWith('llm-')){
	    print(">>LLM", params)
	    return _._onmessage(params)
	}else
	    print(">>ERR", params)}
    _ondatabase(params){
	var used = false;
	if(params.content=="listConvos"){
	    used = true
	    print("LIST", _.uuid, params.results)
	    params.results.forEach(x=>{
		print("X", x[0], " - ", x[1], '!')
		const html = `<a href=.?session=${x[0]}>${x[1]}</a>`
		GEBI("display").appendChild(this.createElt("li", html))
	    })
	}else if(params.content=="newConvo"){
	    used = true
	    print("NEWC", _.uuid, params.results)
	    setTimeout(()=>{
		location = '.'
		/*print("1REFRESH WITH THE NEW CONVO", _.uuid, params.results)
		setTimeout(()=>{
		    print("2REFRESH WITH THE NEW CONVO", _.uuid, params.results)
		    location = '.'
		    print("2REFRESH WITH THE NEW CONVO", _.uuid, params.results)
		},1000)*/
	    },1500)
	}else if(params.content=="shortHistory"){
	    used = true
	    print("SHIST", _.uuid, params.results)
	    params.results.forEach(x=>{
		print(" - X", dumps(x))
		//const html = `<a href=.?session=${x[0]}>${x[1]}</a>`
		//GEBI("display").appendChild(this.createElt("li", html))
	    })
	}
	if(!used)
	    print('WARNING, NOT USED ' + dumps(params))
    }
    _onmessage(params){
	var used = false;
	if(params.thinking){
	    used = true
	    this.appendThoughts(params.thinking)}
	if(params.content){
	    used = true
	    if(params.role=='user' || params.role=='system')
		this.appendMessage(params)
	    else
		this.appendContents(params.content)}
	if(params.done){
	    used = true
	    this.userInputElt().focus()}
	if(!used)
	    print('WARNING, NOT USED ' + dumps(params))
	return this.bot()}
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
const sys = (content, channel)=> app.pub(content, 'system')
const user= (content, channel)=> app.pub(content)
const ls  = ()=>app.listConvos()
const newc= ()=>app.newConvo()
window._ = app
