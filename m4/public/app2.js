const app = (new class App extends WsApp {
    _ondata(params){
	print("DATA", dumps(params))
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
