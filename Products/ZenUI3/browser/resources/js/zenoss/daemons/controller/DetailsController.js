/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    /**
     * @class Daemons.controller.DetailsController
     * This is the controller for the details section of the page.
     * @extends Ext.app.Controller
     */
    Ext.define('Daemons.controller.DetailsController', {
        extend: 'Ext.app.Controller',
        views: [
            "daemons.Details"
        ],
        refs: [{
            ref: 'cardContainer',
            selector: 'daemonsdetails'
        }],
        init: function() {
            // setup controller actions
        },
        /**
         * Sets the context for the detailed view.
         * Depending on the type of the node selected this
         * toggles which pages are available as well as populates
         * the page information
         **/
        setContext: function(uid) {
            var container = this.getCardContainer();
            // every time we select a node completely destroy the form and recreate it
            // as it could be different depending on the context
            if (Ext.getCmp('edit_panel')) {
                container.remove(Ext.getCmp('edit_panel'), true);
            }

            Zenoss.form.getGeneratedForm(uid, function(config){
                container.add(Ext.apply({id:'edit_panel',
                                         autoScroll: true
                                        }, config));
                container.layout.setActiveItem('edit_panel');
            });
        }
    });
})();
