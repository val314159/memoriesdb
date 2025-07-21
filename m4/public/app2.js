const app = (new class App extends WsApp {
    _onpub(params){
	print("PARAMS", dumps(params))
	var used = false;
	if(params.thinking){
	    used = true
	    this.appendThoughts(params.thinking)
	}
	if(params.content){
	    used = true
	    if(params.role!='user'){	
		this.appendContents(params.content)
		return
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
    }
    top(){window.scrollTo(0, 0)}
    bot(){window.scrollTo(0, document.body.scrollHeight)}
}).connect()
const sys = (content, channel)=> app.pub(content, 'system')
const user= (content, channel)=> app.pub(content)
