const GEBI = x=>document.getElementById(x)
const DB_IN = 'db-in'
const app = (new class App extends WsApp {
    displayText(s){
	print(s)
	GEBI("display").appendChild(document.createTextNode(s))
	GEBI("display").appendChild(document.createElement("br"))
    }
    listConvos(){
	this.displayText("LIST CONVOS: " + this.uuid)
	this.displayText("PUBLISH A MESSAGE TO A MICROSERVICE?")
	this.pub('listConvos', 'user', DB_IN)	
    }
    newConvo(){
	this.displayText("NEW CONVO: " + this.uuid)
	this.displayText("PUBLISH A MESSAGE TO A MICROSERVICE?")
	this.pub('newConvo', 'user', DB_IN)	
    }
    top(){window.scrollTo(0, 0)}
    bot(){window.scrollTo(0, document.body.scrollHeight)}
    incrLastId()     {return ++this.lastId}
    inputElt()       {return GEBI(   "input-"+app.lastId)}
    thoughtsElt()    {return GEBI("thinking-"+app.lastId)}
    contentsElt()    {return GEBI( "content-"+app.lastId)}
    userInputElt()   {return GEBI(   "input")}
    displayElt()     {return GEBI(   "display")}
    appendThoughts(s){this.thoughtsElt().appendChild(document.createTextNode(s))}
    appendContents(s){this.contentsElt().appendChild(document.createTextNode(s))}
    _onpub(params){
	//print("PARAMS", dumps(params))
	var used = false;
	if(params.thinking){
	    used = true
	    this.appendThoughts(params.thinking)
	}
	if(params.content){
	    used = true
	    if(params.role!='user'){	
		this.appendContents(params.content)
		return this.bot()
	    }
	    const id = this.incrLastId()
	    const displayElt = this.displayElt()
	    const message = document.createElement("message")
	    message.innerHTML = `\
<message id="message-${id}">
  <div      id="input-${id}">${params.role}${id} // </thinking>
${params.content}</div>
  <thinking id="thinking-${id}">thinking${id} // </thinking>
  <content  id="content-${id}">  content${id} // </content>
</message>`
	    displayElt.appendChild(message)	    
	}
	if(params.done){
	    used = true
	    this.userInputElt().focus()
	}
	if(!used){
	    print("WARNING, NOT USED " + dumps(params))
	}
	return this.bot()
    }
    keypress(e){
	if(e.key!='Enter')return
	//console.log("KEYPRESS1 "+e.key)
	const input = e.target.value.trim()
	e.target.value = ''
	e.target.blur()
	if(!input)return
	//e.target.focus()
	console.log("INPUT "+input)
	user(input)
	return this.bot()
    }
}).connect()
const sys = (content, channel)=> app.pub(content, 'system')
const user= (content, channel)=> app.pub(content)
