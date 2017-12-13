// Express App Setup
const express = require('express')
const app = express()

// Spotify API Setup
const SpotifyWebApi = require('spotify-web-api-node')
const client_id = '00b19d27375945309907da13aabb4220'
const client_secret = '09581a2af6ef4982b904d60bbe8aba6a'
const redirect_uri  = 'http://localhost:3000/spotifycallback'

var spotifyApi = new SpotifyWebApi({
    clientId : client_id,
    clientSecret : client_secret,
    redirectUri : 'http://localhost:3000/spotifycallback'
})

// Hue API Setup
var hue = require('node-hue-api'),
HueApi = hue.HueApi,
lightState = hue.lightState,
//host = '192.168.0.100', // Max's bridge
// username = 'JShMgr2F2OmUu5ZebZQtUTNsg0bkgUH0VjeG4qg5', // Max's bridge
host = '192.168.1.141', // Tim's bridge
username = 'AqV0Pfsfnm1OQBnFDL2bf5HxkAKYHldbLw9MbF4m', // Tim's bridge
availableLights = []
var bridge = new HueApi(host,username)

bridge.lights()
.then((data) => {
    availableLights = data.lights.filter((elem) => {
        return elem.state.reachable == true
    })
    availableLights = availableLights.map((elem) => {
        return elem.id
    })
    console.log("Available Lights: " + availableLights)
})

// Custom Light States
let state1 = lightState.create().on().rgb(253,154,95).bri(255) // Orange-Yellow
let state2 = lightState.create().off() // Off
let state3 = lightState.create().on().rgb(216,245,255).bri(255) // White-Blue
let state4 = lightState.create().on().rgb(255,249,191).bri(255) // White-Yellow
let state5 = lightState.create().on().rgb(233,170,255).bri(255) // Light Purple
let state6 = lightState.create().on().rgb(80,95,255).bri(255) // Blue purple
let resetState = lightState.create().on().rgb(255,255,255).bri(200) // White moderate bright

// Spotify Playlists
let chillHipHop = 'spotify:user:chillhopmusic:playlist:74sUjcvpGfdOvCHvgzNEDO'
let funkst = 'spotify:user:spotify:playlist:37i9dQZF1DX7Q7o98uPeg1'
let brainfood = 'spotify:user:spotify:playlist:37i9dQZF1DWXLeA8Omikj7'
let jazztronica = 'spotify:user:spotify:playlist:37i9dQZF1DX55dNU0PWnO5'
let piano = 'spotify:user:spotify:playlist:37i9dQZF1DX4sWSpwq3LiO'
let deepfocus = 'spotify:user:spotify:playlist:37i9dQZF1DWZeKCadgRdKQ'

// Trancendance Obejct
const Trancendance = [
    {
        playlistID: chillHipHop,
        lState: state1
    },
    {
        playlistID: piano,
        lState: state2
    },
    {
        playlistID: brainfood,
        lState: state3
    },
    {
        playlistID: deepfocus,
        lState: state4
    },
    {
        playlistID: jazztronica,
        lState: state5
    },
    {
        playlistID: funkst,
        lState: state6
    }
]

// Express Router
app.get('/', (req, res) => res.send('Transcendance'))

// -------------------- //
// Hue Interface Routes //
// -------------------- //
app.get('/huestate/',(req,res) => {
    bridge.getFullState().then((result) => {
        return res.json(result)
    }).catch((err) => {
        return res.send("Error: " + err)
    })
})

app.get('/rgb/:r/:g/:b/:bri',(req,res) => {
    let r = req.params.r,
        g = req.params.g,
        b = req.params.b,
        bri = req.params.bri || 255

    let lightPromises = availableLights.map((lightID) => {
        return bridge.setLightState(lightID,lightState.create().on().rgb(r,g,b).bri(bri))
    })
    Promise.all(lightPromises)
    .then(() => {
        return res.send("Hue Lights Updated")
    }).catch((err) => {
        return res.status(500).send("Issue addressing one or more lights")
    })
})

// ------------------------ //
// Spotify Interface Routes //
// ------------------------ //
app.get('/login', (req,res) => {
    var scopes = "user-modify-playback-state user-read-playback-state "
    res.redirect('https://accounts.spotify.com/authorize' + 
    '?response_type=code' +
    '&client_id=' + client_id +
    (scopes ? '&scope=' + encodeURIComponent(scopes) : '') +
    '&redirect_uri=' + encodeURIComponent(redirect_uri));
})

// Spotify API callback code adapted from example:
// https://github.com/thelinmichael/spotify-web-api-node/blob/master/examples/access-token-refresh.js
app.get('/spotifycallback', (req,res) => {
    let code = req.query.code || null;
    if (code != null) {
        console.log("Code obtained: " + code)
        spotifyApi.authorizationCodeGrant(code)
        .then(function(data) {
            // Set the access token and refresh token
            spotifyApi.setAccessToken(data.body['access_token'])
            spotifyApi.setRefreshToken(data.body['refresh_token'])
    
            // Save the amount of seconds until the access token expired
            tokenExpirationEpoch = (new Date().getTime() / 1000) + data.body['expires_in']
            let secondsRemaining = Math.floor(tokenExpirationEpoch - new Date().getTime() / 1000)
            console.log('Retrieved token. It expires in ' + secondsRemaining + ' seconds!')

            // Set timer to tell us when the token expires
            setInterval(() => {
                console.log('Token expired.')
                spotifyApi.refreshAccessToken()
                .then(function(data) {
                    console.log("Token refreshed")
                }, function(err) {
                    console.log('Could not refresh the token!', err.message)
                })
            }, secondsRemaining * 1000)
            return res.redirect('/success')
        }, function(err) {
            console.log('Something went wrong when retrieving the access token!', err.message)
            return res.redirect('/error')
        });
    } else {
        console.log("Code was null. Here's a log of the request query:")
        console.log(req.query)
        return res.redirect('/error')
    }
})

app.get('/success',(req,res) => {
    res.send("Successful Login")
})

app.get('/error', (req,res) => {
    res.send("Error Logging In. Check Logs")
})

app.get('/play/:playlistID',(req,res) => {
    let plID = req.params.playlistID || null;
    let spotifyArgs = {}
    if (plID != '') {
        spotifyArgs.context_uri = plID
    }
    spotifyApi.play(spotifyArgs)
    .then(data => {
        return res.status(data.statusCode).send("Status Code: " + data.statusCode)
    }).catch((err) => {
        return res.status(500).send(err)
    })
})

app.get('/pause',(req,res) => {
    spotifyApi.pause()
    .then(data => {
        return res.status(data.statusCode).send("Status Code: " + data.statusCode)
    }).catch((err) => {
        return res.status(500).send(err)
    })
})

app.get('/listdevices',(req,res) => {
    spotifyApi.getMyDevices()
    .then(data => {
        return res.status(data.statusCode).json(data.body)
    }).catch((err) => {
        return res.status(500).send(err)
    })
})

// ---------------- //
// Trancendance API //
// ---------------- //
app.get('/state/:num',(req,res) => {
    let combo = req.params.num
    let state = Trancendance[combo]
    
    // Spotify state
    let spotifyArgs = {
        context_uri: state.playlistID
    }
    spotifyApi.setShuffle({state:true}).then((data) => {
        return spotifyApi.play(spotifyArgs)
    }).then((data) => {
        if (data.statusCode != 204) {
            return res.status(500).send("Error with Spotify Play function")
        }
    }).then(() => {
        let lightPromises = availableLights.map((lightID) => {
            return bridge.setLightState(lightID,state.lState)
        })
        return Promise.all(lightPromises)
    }).then(() => {
        return res.send("Done")
    }).catch((err) => {
        return res.status(500).send("Error: " + err)
    })
})

app.get('/reset',(req,res) => {
    // Set the lightState to moderate bright
    // Music to pause
    spotifyApi.pause()
    .then((result) => {
        let lightPromises = availableLights.map((lightID) => {
            return bridge.setLightState(lightID,resetState)
        })
        return Promise.all(lightPromises)
    }).then(() => {
        return res.send("Reset Done")
    }).catch((err) => {
        return res.status(500).send("Error: " + err)
    })
})

app.listen(3000, () => console.log('Example app listening on port 3000!'))