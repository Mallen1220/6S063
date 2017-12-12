const express = require('express')
const app = express()
const request = require('request')
const hue = require('node-hue-api'),
    HueApi = hue.HueApi,
    lightState = hue.lightState

var host = '192.168.0.100',
    username = 'JShMgr2F2OmUu5ZebZQtUTNsg0bkgUH0VjeG4qg5'

var api = new HueApi(host,username)

// Custom Light States
let state1 = lightState.create().on(true).bri(255).hue(35000)
let state2 = lightState.create().off()

app.get('/', (req, res) => res.send('Hello World!'))

app.get('/state/',(req,res) => {
    api.getFullState().then((result) => {
        res.json(result)
    }).catch((err) => {
        res.send("Error: " + err)
    }).done()
})

app.get('/test/on',(req,res) => {
    // request({
    //     method: 'PUT',
    //     uri: 'http://192.168.1.141/api/vHGQAWI3MKJw55hDNMD6kXVweKHFPI105M9vnBvm/lights/4/state',
    //     json: true,
    //     body: {on:true}
    // }, (err,res,body) => {
    //     if (err) {
    //         console.log(err)
    //     }
    // })
    api.setLightState('5',lightState.create().on())
    res.send("Turned On")
})


app.get('/test/off',(req,res) => {
    // request({
    //     method: 'PUT',
    //     uri: 'http://192.168.1.141/api/vHGQAWI3MKJw55hDNMD6kXVweKHFPI105M9vnBvm/lights/4/state',
    //     json: true,
    //     body: {on:false}
    // }, (err,res,body) => {
    //     if (err) {
    //         console.log(err)
    //     }
    // })
    api.setLightState('5',lightState.create().off())
    res.send("Turned Off")
})

app.listen(3000, () => console.log('Example app listening on port 3000!'))