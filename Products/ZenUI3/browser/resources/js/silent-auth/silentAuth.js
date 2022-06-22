var silentAuthNS = {
    auth0_cz: new auth0.WebAuth({
        domain: window.ZC_CONFIG.AUTH0_DOMAIN,
        clientID: window.ZC_CONFIG.AUTH0_CLIENT_ID,
        redirectUri: window.location.origin + "/auth.html",
        audience: window.ZC_CONFIG.AUTH0_AUDIENCE,
        responseType: "token id_token",
        scope: "openid profile"
    }),
    getStorageValue: function (key) {
        return JSON.parse(localStorage.getItem(key))
    },
    setStorageValue: function (key, val) {
        return localStorage.setItem(key, JSON.stringify(val))
    },
    isAuthenticated: function () {
        if (this.getStorageValue("accessToken")) {
            var exp = new Date(+this.getStorageValue("accessTokenExpiration"))
            if (exp && (exp < (Date.now() + 30000))) { // make sure that token not expire before next check
                return false
            }
            if (!Cookies.get("accessToken")) {
                Cookies.set("accessToken", this.getStorageValue("accessToken"), {
                    secure: true
                })
            }
            return true
        }
        return false
    },
    authenticateSilently: function () {
        this.auth0_cz.checkSession({}, (err, result) => {
            if (err) {
                console.log(err);
            } else if (result) {
                if (result.accessToken) {
                    this.setStorageValue("accessToken", result.accessToken);
                    Cookies.set("accessToken", result.accessToken, {
                        secure: true
                    })
                } else {
                    console.log("No access token received from Auth0");
                }
                if (result.idToken) {
                    this.setStorageValue("idToken", result.idToken)
                }
                if (result.expiresIn && result.idTokenPayload && result.idTokenPayload.iat) {
                    var tokenExp = String((result.expiresIn + result.idTokenPayload.iat) * 1000)
                    Cookies.set("accessTokenExpiration", tokenExp, {
                        secure: true
                    })
                    this.setStorageValue("accessTokenExpiration", tokenExp)
                }
                if (result.idTokenPayload) {
                    var name = "unknown"
                    var tpName = result.idTokenPayload.name
                    var tpGiven = result.idTokenPayload.given_name
                    var tpFamily = result.idTokenPayload.family_name
                    var tpNick = result.idTokenPayload.nickname

                    if (tpName) {
                        name = tpName
                    } else if (tpGiven || tpFamily) {
                        name = tpGiven && tpFamily ? `${tpGiven} ${tpFamily}` : tpGiven || tpFamily
                    } else if (tpNick) {
                        name = tpNick
                    }

                    var username = tpNick
                    if (name === tpNick || name === "unknown") {
                        username = result.idTokenPayload.sub.split("|").pop()
                    }

                    var audience = this.auth0_cz.baseOptions.audience
                    var tenant = result.idTokenPayload[`${audience}/tenant`]
                    this.setStorageValue("userInfo", {
                        id: result.idTokenPayload.sub,
                        name,
                        username,
                        picture: result.idTokenPayload.picture || "",
                        tenant,
                        locale: result.idTokenPayload.locale,
                        roles: result.idTokenPayload["https://zenoss.com/roles"]
                    })
                }
                if (result.scope) {
                    this.setStorageValue("userScope", result.scope);
                }
                console.log("Silently authenticate successfuly")
            } else {
                console.log("No auth info received from Auth0");
            }
        })
    },
    silentReauth: function () {
        if (!this.isAuthenticated()) {
            this.authenticateSilently();
        }
    }
}

window.onload = function() {
    silentAuthNS.silentReauth();
    setInterval(() => silentAuthNS.silentReauth(), 30000);
}
