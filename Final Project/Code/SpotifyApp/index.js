const express = require('express')
const SpotifyWebApi = require('spotify-web-api-node')
const client_id = '00b19d27375945309907da13aabb4220'
const client_secret = '09581a2af6ef4982b904d60bbe8aba6a'
const redirect_uri  = 'http://localhost:3000/spotifycallback'

var spotifyApi = new SpotifyWebApi({
    clientId : client_id,
    clientSecret : client_secret,
    redirectUri : 'http://localhost:3000/spotifycallback'
})

var app = express()

app.get('/',(req,res) => {
    res.send("Transcendance")
})

app.get('/login', (req,res) => {
    var scopes = "user-modify-playback-state user-read-playback-state "
    res.redirect('https://accounts.spotify.com/authorize' + 
    '?response_type=code' +
    '&client_id=' + client_id +
    (scopes ? '&scope=' + encodeURIComponent(scopes) : '') +
    '&redirect_uri=' + encodeURIComponent(redirect_uri));
})

// Code adapted from example:
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
            console.log('Retrieved token. It expires in ' + Math.floor(tokenExpirationEpoch - new Date().getTime() / 1000) + ' seconds!')

            // Set timer to tell us when the token expires
            setInterval(() => {
                console.log('Token expired.')
                // spotifyApi.refreshAccessToken()
                // .then(function(data) {
                //     // Do something, like calling refresh in another 3600 secs
                // }, function(err) {
                //     console.log('Could not refresh the token!', err.message)
                // })
            }, Math.floor(tokenExpirationEpoch - new Date().getTime() / 1000))
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

app.post('/spotifycallback', (req,res) => {
    console.log("POST to spotify callback")
})

app.get('/play/:playlistID',(req,res) => {
    spotifyApi.play()
    .then(data => {
        res.send("Status Code: " + data.statusCode)
    })
})

app.get('/pause',(req,res) => {
    spotifyApi.pause()
    .then(data => {
        res.send("Status Code: " + data.statusCode)
    })
})

app.get('/listdevices',(req,res) => {
    spotifyApi.getMyDevices()
    .then(data => {
        res.json(data.body)
    })
})

app.listen(3000,() => {
    console.log("Server listening on port 3000")
})