/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2018, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

 /*
    generic tracker wrapper
    description:    provides user-tracking to pages
                    via an analytics-agnostic interface
    usage:

        this.tracker.hit({
            category: "report",
            action: action,
            label: label || this.config.id
        })

*/

// set dimension1 variable with domain name
window.ga('set', 'dimension1', document.domain);

function hit(config){
    let {category, action, label, value} = config
    window.ga("send", "event", category, action, label, value, {
        hitCallback: () => {
            console.log("tracked event", category, action, label, value)
        }
    })
}

