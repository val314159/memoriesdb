const  app = (new class App extends WsApp {
    _ondata(params){
	print("DATA", dumps(params))
    }
}).connect()
const  sys = (content, channel)=> app.pub(content, 'system')
const user = (content, channel)=> app.pub(content)
