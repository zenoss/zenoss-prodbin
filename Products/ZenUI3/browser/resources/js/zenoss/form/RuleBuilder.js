(function() {

    var ZF = Ext.ns('Zenoss.form.rule');

    ZF.CONJUNCTIONS = {
        any: {
            text: _t('any'),
            tpl: ' or '
        },
        all: {
            text: _t('all'),
            tpl: ' and '
        }
    };

    var buttons = function(scope) {
        return [{
            xtype: 'button',
            ref: 'buttonAdd',
            iconCls: 'add',
            handler: function() {
                var realowner = scope.ownerCt,
                idx = realowner.items.indexOf(scope);
                var clause = realowner.insert(idx + 1, {
                    xtype: 'ruleclause'
                });
                realowner.doLayout();
                clause.subject.focus();
            },
            scope: scope
        },{
            xtype: 'button',
            ref: 'buttonDelete',
            iconCls: 'delete',
            handler: function() {
                scope.ownerCt.remove(scope, true /* autoDestroy */);
                scope.getBuilder().fireEvent('rulechange', scope);
            },
            scope: scope
        },{
            xtype: 'button',
            ref: 'buttonSubclause',
            iconCls: 'classify',
            handler: function() {
                var realowner = scope.ownerCt,
                idx = realowner.items.indexOf(scope);
                realowner.insert(idx + 1, {
                    xtype: 'nestedrule'
                });
                realowner.doLayout();
            },
            scope: scope
        }];
    };

    ZF.CONJUNCTION_STORE = [];
    for (var conjunction in ZF.CONJUNCTIONS) {
        if (ZF.CONJUNCTIONS.hasOwnProperty(conjunction)) {
            var text = ZF.CONJUNCTIONS[conjunction].text;
            ZF.CONJUNCTION_STORE.push([conjunction, text]);
        }
    }

    ZF.COMPARISONS = {
        contains: {
            text: _t('contains'),
            tpl: '{1} in {0}'
        },
        startswith: {
            text: _t('starts with'),
            tpl: '{0}.startswith({1})'
        },
        endswith: {
            text: _t('ends with'),
            tpl: '{0}.endswith({1})'
        },
        doesnotcontain: {
            text: _t('does not contain'),
            tpl: '{1} not in {0}'
        },
        doesnotstartwith: {
            text: _t('does not start with'),
            tpl: 'not {0}.startswith({1})'
        },
        doesnotendwith: {
            text: _t('does not end with'),
            tpl: 'not {0}.endswith({1})'
        },
        equals: {
            text: _t('equals'),
            tpl: '{0} == {1}'
        },
        doesnotequal: {
            text: _t('does not equal'),
            tpl: '{0} != {1}'
        },
        lessthan: {
            text: _t('less than'),
            tpl: '{0} < {1}',
            field: {xtype: 'numberfield'}
        },
        greaterthan: {
            text: _t('greater than'),
            tpl: '{0} > {1}',
            field: {xtype: 'numberfield'}
        },
        lessthanorequalto: {
            text: _t('less than or equal to'),
            tpl: '{0} <= {1}',
            field: {xtype: 'numberfield'}
        },
        greaterthanorequalto: {
            text: _t('greater than or equal to'),
            tpl: '{0} >= {1}',
            field: {xtype: 'numberfield'}
        /*},
        between: {
            text: _t('between'),
            tpl: '{1} <= {0} <= {2}'
        */
        }
    };
    ZF.COMPARISON_STORE = [];
    for (var comparison in ZF.COMPARISONS) {
        if (ZF.COMPARISONS.hasOwnProperty(comparison)) {
            var jtext = ZF.COMPARISONS[comparison].text;
            ZF.COMPARISON_STORE.push([comparison, jtext]);
        }
    }

    ZF.RuleClause = Ext.extend(Ext.Toolbar, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                cls: 'rule-clause',
                items: [{
                    ref: 'subject',
                    xtype: 'combo',
                    allowBlank: false,
                    editable: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    hiddenName: 'doesntmatter',
                    store: [[null,null]],
                    getSubject: function() {
                        return this.getBuilder().subject_map[this.subject.hiddenField.value];
                    }.createDelegate(this),
                    listeners: {
                        valid: function() {
                            // Get the associated subject
                            var subject = this.subject.getSubject(),
                                comparisons = [];

                            // Update comparisons
                            if (subject.comparisons) {
                                Ext.each(subject.comparisons, function(cmp) {
                                    var c = ZF.COMPARISONS[cmp];
                                    if (!c) {
                                        return;
                                    }
                                    var jtext = c.text;
                                    comparisons.push([cmp, jtext]);
                                });
                            } else {
                                comparisons = ZF.COMPARISON_STORE;
                            }
                            this.comparison.store.loadData(comparisons);
                            this.comparison.setValue(comparisons[0][0]);

                            this.getBuilder().fireEvent(
                                'rulechange',
                                this
                            );
                        },
                        scope: this
                    }
                },{
                    ref: 'comparison',
                    hiddenName: 'doesntmatter',
                    xtype: 'combo',
                    editable: false,
                    allowBlank: false,
                    store: ZF.COMPARISON_STORE,
                    value: ZF.COMPARISON_STORE[0][0],
                    forceSelection: true,
                    triggerAction: 'all',
                    listeners: {
                        valid: function() {
                            var cmp = ZF.COMPARISONS[this.comparison.hiddenField.value],
                                field = this.subject.getSubject().field || cmp.field || {xtype:'textfield'};
                            var idx = this.items.items.indexOf(this.predicate);
                            this.remove(this.predicate);
                            this.insert(idx, Ext.apply({
                                ref: 'predicate',
                                listeners: {
                                    valid: function() {
                                        this.getBuilder().fireEvent(
                                            'rulechange',
                                            this
                                        );
                                    },
                                    scope: this
                                }
                            }, field));
                            this.doLayout();
                            this.getBuilder().fireEvent(
                                'rulechange',
                                this
                            );
                            this.predicate.focus();
                        },
                        scope: this
                    }
                },{
                    ref: 'predicate',
                    xtype: 'textfield',
                    listeners: {
                        valid: function() {
                            this.getBuilder().fireEvent(
                                'rulechange',
                                this
                            );
                        },
                        scope: this
                    }
                },'->']
            });
            Ext.each(buttons(this), function(btn) {
                config.items.push(btn);
            });
            ZF.RuleClause.superclass.constructor.call(this, config);
            var subjects = this.getBuilder().subject_store;
            this.subject.store.loadData(subjects);
            this.subject.setValue(subjects[0][0]);
            this.on('added', function(){
                this.getBuilder().fireEvent('rulechange', this);
            }, this);
        },
        getValue: function() {
            var field = this.comparison.hiddenField,
                sub = this.subject.getValue(),
                pred = this.predicate.getValue();
            if (!field || !sub || !pred) { return; }
            var cmp = ZF.COMPARISONS[field.value];
            return String.format(cmp.tpl, this.getBuilder().prefix + sub, Ext.encode(pred));
        },
        getBuilder: function() {
            if (!this.builder) {
                this.builder = this.findParentByType('rulebuilder', true);
            }
            return this.builder;
        }
    });

    Ext.reg('ruleclause', ZF.RuleClause);

    ZF.changeListener = function(me, cmp) {
        var items = this.items.items;

        // If we're somewhere in the middle of initialization don't do anything
        if (items.length===0) {
            return;
        } 

        var item = items[0],
            delbtn = item instanceof ZF.NestedRule ?
                     item.items.items[0].buttonDelete :
                     item.buttonDelete;

        // Disable the delete button if only one at this level
        if (items.length==1) {
            delbtn.disable();
        } else if (items.length > 1){
            delbtn.enable();
        }

        // Disable the nested button if it would mean more than 4 deep
        var i = 0, btn;
        while (item = item.findParentByType('nestedrule')) {
            i++;
            if (i>=4) {
                if (btn = cmp.buttonSubclause) {
                    btn.disable();
                }
                break;
            }
        }
    };

    ZF.NestedRule = Ext.extend(Ext.Container, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                showButtons: true,
                cls: 'nested-rule',
                items: [{
                    xtype: 'toolbar',
                    cls: 'rule-clause nested-rule-header',
                    items: [{
                        ref: '../conjunction',
                        xtype: 'combo',
                        width: 60,
                        store: ZF.CONJUNCTION_STORE,
                        editable: false,
                        allowBlank: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        value: 'all',
                        listeners: {
                            valid: function() {
                                this.getBuilder().fireEvent(
                                    'rulechange',
                                    this
                                );
                            },
                            scope: this
                        }
                    },{
                        xtype: 'tbtext',
                        html: _t('of the following rules:'),
                        style: 'margin-left: 7px; font-size: 12px; color: #444'
                    }]
                },{
                    ref: 'clauses',
                    xtype: 'container',
                    cls: 'rule-clause-container',
                    items: {
                        xtype: 'ruleclause'
                    },
                    listeners: {
                        add: ZF.changeListener,
                        remove: ZF.changeListener
                    }
                }]
            });
            if (config.showButtons) {
                var items = config.items[0].items;
                items.push('->');
                Ext.each(buttons(this), function(btn) {
                    items.push(btn);
                });
            }
            ZF.NestedRule.superclass.constructor.call(this, config);
        },
        getBuilder: function() {
            if (!this.builder) {
                this.builder = this.findParentByType('rulebuilder', true);
            }
            return this.builder;
        },
        getValue: function() {
            var values = [],
                joiner = ZF.CONJUNCTIONS[this.conjunction.getValue()].tpl;
            Ext.each(this.clauses.items.items, function(clause) {
                var value = clause.getValue();
                if (value) {
                    values.push(String.format("({0})", value));
                }
            }, this);
            return values.join(joiner);
        }
    });

    Ext.reg('nestedrule', ZF.NestedRule);

    ZF.RuleBuilder = Ext.extend(Ext.Container, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                cls: 'rule-builder',
                prefix: '',
                width: 690,
                items: [{
                    ref: 'rootrule',
                    xtype: 'nestedrule',
                    showButtons: false
                }]
            });
            this.subject_store = [];
            this.subject_map = {};
            Ext.each(config.subjects, function(subject) {
                if (!Ext.isObject(subject)) {
                    subject = {value: subject};
                }
                this.subject_store.push([subject.value, subject.text || subject.value]);
                this.subject_map[subject.value] = subject;
            }, this);
            ZF.RuleBuilder.superclass.constructor.call(this, config);
            this.addEvents('rulechange');
        },
        getValue: function() {
            return this.rootrule.getValue();
        }
    });

    Ext.reg('rulebuilder', ZF.RuleBuilder);

    ZF.NUMBERCOMPARISONS = [
        'equals',
        'doesnotequal',
        'lessthan',
        'greaterthan',
        'lessthanorequalto',
        'greaterthanorequalto'
    ];

    ZF.IDENTITYCOMPARISONS = [
        'equals',
        'doesnotequal'
    ];

    Ext.apply(ZF, {
        PRODUCTIONSTATE: {
            text: _t('Production state'),
            value: 'productionState',
            field: { 
                xtype: 'ProductionStateCombo'
            },
            comparisons: ZF.NUMBERCOMPARISONS
        },
        DEVICEPRIORITY: {
            text: _t('Device priority'),
            value: 'priority',
            field: {
                xtype: 'PriorityCombo'
            },
            comparisons: ZF.NUMBERCOMPARISONS
        },
        DEVICE: {
            text: _t('Device'),
            value: 'device_uuid',
            comparisons: ZF.IDENTITYCOMPARISONS,
            field: {
                xtype: 'combo',
                mode: 'remote',
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getDeviceUuidsByName,
                    root: 'data',
                    fields: ['name', 'uuid']
                }),
                typeAhead: true,
                valueField: 'uuid',
                displayField: 'name',
                forceSelection: true,
                triggerAction: 'all'
            }
        }
    });

})();
