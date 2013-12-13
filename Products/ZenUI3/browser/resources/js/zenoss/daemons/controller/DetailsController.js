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
        }, {
            ref: 'menuCombo',
            selector: 'combobox[ref="menucombo"]'
        }],
        init: function() {
            this.control({
                'daemonsdetails combobox[ref="menucombo"]': {
                    select: this.changeDetailsView
                }
            });

            /**
             * This structure ties the combo menu to the
             * cards of the cardlayout panel.
             **/
            this.detailActions = {
                menu: {
                    hub: [
                        {id: 'graphs', name: _t('Graphs')},
                        {id: 'details', name: _t('Details')}
                    ],
                    collector: [
                        {id: 'graphs', name: _t('Graphs')},
                        {id: 'details', name: _t('Details')},
                        {id: 'collectordevices', name: _t('Devices')}
                    ],
                    daemon: [
                        {id: 'details', name: _t('Details')}
                    ]
                },
                actions: {
                    hub: {
                        details: this.setDetailsPanel,
                        graphs: this.setGraphs
                    },
                    collector: {
                        details: this.setDetailsPanel,
                        collectordevices: this.setDevices,
                        graphs: this.setGraphs
                    },
                    daemon: {
                        details: this.setDaemonDetailsPanel
                    }
                }
            };
        },
        /**
         * This method is responsible for showing the card that
         * corresponds to the selected menu item.
         **/
        changeDetailsView: function(combo, selected) {
            var card = selected[0];
            // in order for this to work the id of the model item in the
            // combobox must match the id of the card we want to display
            this.getCardContainer().layout.setActiveItem(card.get('id'));

            // refresh the view
            if (this.selected) {
                this.setContext(this.selected);
            }
        },
        /**
         * Sets the context for the detailed view.
         * Depending on the type of the node selected this
         * toggles which pages are available as well as populates
         * the page information
         **/
        setContext: function(selected) {
            this.selected = selected;
            this.setDetailsMenu();
        },
        syncMenus: function(type){
            var store = this.getMenuStore(type),
                combo = this.getMenuCombo(),
                value = combo.getValue();
            if (!store.getById(value)) {
                value = 'details';
            }
            combo.bindStore(store, true);
            combo.setValue(value);
        },
        setDetailsMenu: function() {
            var type = this.selected.get('type');
            this.syncMenus(type);
            var actions = this.detailActions.actions[type],
                selectedMenuItem = this.getMenuCombo().getValue(),
                action = actions[selectedMenuItem];
            Ext.bind(action, this)();
        },
        setDetailsPanel:function(router) {
            var container = this.getCardContainer(),
                selected = this.selected;
            // every time we select a node completely destroy the form and recreate it
            // as it could be different depending on the context
            if (Ext.getCmp('edit_panel')) {
                container.details.remove(Ext.getCmp('edit_panel'), true);
            }

            Zenoss.form.getGeneratedForm(selected.get("uid"), function(config){
                container.details.add(Ext.apply({id:'edit_panel',
                                         autoScroll: true
                                        }, config));
                container.layout.setActiveItem(container.details);
            }, router);
        },
        setDaemonDetailsPanel: function() {
            this.setDetailsPanel(Zenoss.remote.ApplicationRouter);
        },
        setDevices: function() {
            // setup a filter to only show devices for this collector
            var grid = this.getCardContainer().devices,
                selected = this.selected;
            // set the parameter in the store
            grid.getStore().setParamsParam('collector', selected.get('name'));
            // display that it is filtered by collector in case that
            // column is visible
            grid.setFilter('collector', selected.get('name'));
        },
        setGraphs: function() {
            this.getCardContainer().graphs.setContext(this.selected.get('uid'));
        },
        refreshDevices: function() {
            this.getCardContainer().devices.refresh();
        },
        /**
         * This is a factory method for fetching the appropiate menu based
         * on the type. Type can be collector, application or hub
         **/
        getMenuStore: function(type) {
            var menu = Ext.create('Ext.data.Store', {
                fields: ['id', 'name'],
                idProperty: 'id',
                data : this.detailActions.menu[type]
            });
            return menu;
        }
    });
})();
