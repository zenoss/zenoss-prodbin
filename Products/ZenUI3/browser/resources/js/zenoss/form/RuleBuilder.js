(function() {

    var ZF = Ext.ns('Zenoss.form.rule'),
         unparen=/^\((.*)\)$/,
         nested=/\)( and | or )\(/,
         conjunctions_inverse = {};

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
            var conj = ZF.CONJUNCTIONS[conjunction];
            ZF.CONJUNCTION_STORE.push([conjunction, conj.text]);
            conjunctions_inverse[conj.tpl.trim()] = conjunction;
        }
    }

    
    /*
     *  The order of the comparisons in the following object matters. The
     *  templates are used to create regular expressions where the {#} substitutions
     *  get replaced with '(.*)'. When loading a clause, the following object
     *  is iterated over and the first matching regular expression gets used to
     *  parse the clause.
     */
    ZF.COMPARISONS = {
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
        equals: {
            text: _t('equals'),
            tpl: '{0} == {1}'
        },
        doesnotequal: {
            text: _t('does not equal'),
            tpl: '{0} != {1}'
        },
        lessthan: {
            text: _t('is less than'),
            tpl: '{0} < {1}',
            field: {xtype: 'numberfield'}
        },
        greaterthan: {
            text: _t('is greater than'),
            tpl: '{0} > {1}',
            field: {xtype: 'numberfield'}
        },
        lessthanorequalto: {
            text: _t('is less than or equal to'),
            tpl: '{0} <= {1}',
            field: {xtype: 'numberfield'}
        },
        greaterthanorequalto: {
            text: _t('is greater than or equal to'),
            tpl: '{0} >= {1}',
            field: {xtype: 'numberfield'}
        }
    };
    ZF.COMPARISON_STORE = [];
    var comparison_patterns = {};
    for (var comparison in ZF.COMPARISONS) {
        if (ZF.COMPARISONS.hasOwnProperty(comparison)) {
            var cmp = ZF.COMPARISONS[comparison];
            ZF.COMPARISON_STORE.push([comparison, cmp.text]);
            comparison_patterns[comparison] = new RegExp(
                cmp.tpl.replace('(', '\\(')
                       .replace(')', '\\)')
                       .xsplit(/\{\d+\}/)
                       .join('(.*)'));
        }
    }

    ZF.RuleClause = Ext.extend(Ext.Toolbar, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                cls: 'rule-clause',
                items: [{
                    ref: 'subject',
                    xtype: 'combo',
                    autoSelect: true,
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
                                    comparisons.push([cmp, c.text]);
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
                    autoSelect: true,
                    editable: false,
                    allowBlank: false,
                    store: ZF.COMPARISON_STORE,
                    value: ZF.COMPARISON_STORE[0][0],
                    forceSelection: true,
                    triggerAction: 'all',
                    listeners: {
                        valid: function() {
                            var cmp = ZF.COMPARISONS[this.comparison.hiddenField.value],
                                field = this.subject.getSubject().field || cmp.field || {xtype:'textfield'},
                                idx = this.items.items.indexOf(this.predicate),
                                oldvalue = this.predicate.getValue(),
                                oldxtype = this.predicate.xtype;
                            this.remove(this.predicate);
                            this.insert(idx, Ext.apply({
                                ref: 'predicate',
                                allowBlank: false,
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
                            if (oldvalue && this.predicate.xtype == oldxtype) {
                                this.predicate.setValue(oldvalue);
                            }
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
            if (!field || !sub || Ext.isEmpty(pred)) { return; }
            var cmp = ZF.COMPARISONS[field.value];
            var clause = String.format(cmp.tpl, this.getBuilder().prefix + sub, Ext.encode(pred));
            return String.format("({0})", clause);
        },
        setValue: function(expression) {
            for (var cmp in comparison_patterns) {
                if (comparison_patterns.hasOwnProperty(cmp)) {
                    var pat = comparison_patterns[cmp];
                    if (pat.test(expression)) {
                        var vals = pat.exec(expression).slice(1),
                            spots = pat.exec(ZF.COMPARISONS[cmp].tpl).slice(1),
                            sorted = Ext.zip.apply(this, Ext.zip(spots, vals).sort())[1],
                            subject = sorted[0],
                            value = sorted[1],
                            cleansub = subject.replace(
                                new RegExp("^"+this.getBuilder().prefix), '');
                        this.subject.on('valid', function(){
                            this.comparison.setValue(cmp);
                        }, this, {single:true});
                        this.comparison.on('valid', function(){
                            this.predicate.setValue(Ext.decode(value));
                        }, this, {single:true});
                        this.subject.setValue(cleansub);
                        this.comparison.setValue(cmp);
                        break;
                    }
                }
            }
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
                joiner = ZF.CONJUNCTIONS[this.conjunction.getValue()].tpl,
                result;
            Ext.each(this.clauses.items.items, function(clause) {
                var value = clause.getValue();
                if (value) {
                    values.push(value);
                }
            }, this);
            result = values.join(joiner);
            if (values.length > 1) {
                result = String.format('({0})', result);
            }
            return result;
        },
        setValue: function(expression) {
            var c, q, i=0, p=0, tokens=[], token=[],
                funcflag=false;
            c = expression.charAt(i);
            var savetoken = function() {
                var v = token.join('').trim();
                if (v) {
                    tokens.push(v);
                }
                token = [];
            };
            while (c) {
                //token.push(c);
                // Don't deal with contents of string literals
                if (c=='"'||c=='\'') {
                    q = c;
                    token.push(c);
                    for (;;) {
                        i++;
                        c = expression.charAt(i);
                        token.push(c);
                        if (c===q) {
                            // Closing quote
                            break;
                        }
                        if (c === '\\') {
                            // Skip escaped chars
                            i++;
                            token.push(expression.charAt(i));
                        }
                    }
                } else if (c=="("||c==")"){
                    if (p===0) {
                        savetoken();
                    }
                    token.push(c);
                    if (c=='(') {
                        var prev = expression[i-1];
                        if (i>0 && prev!=' ' && prev!='(') {
                            funcflag = true;
                        } else {
                            p++;
                        }
                    } else if (c==')') {
                        if (funcflag) {
                            funcflag = false;
                        } else {
                            p--;
                        }
                    }
                    if (p===0) {
                        savetoken();
                    }
                } else {
                    token.push(c);
                }
                i++;
                c = expression.charAt(i);
            }
            savetoken();
            if (tokens) {
                this.clauses.removeAll();
                var conjunction, rule;
                Ext.each(tokens, function(t) {
                    if (t) {
                        if (conjunction = conjunctions_inverse[t]){
                             this.conjunction.setValue(conjunction);
                             return;
                        } else if (nested.test(t)) {
                            // Nested rule
                            rule = this.clauses.add({xtype:'nestedrule'});
                        } else {
                            // Clause
                            rule = this.clauses.add({xtype: 'ruleclause'});
                        }
                        var clause = t;
                        try {
                            clause = unparen.exec(t)[1];
                        } catch(ignored) {}
                        rule.setValue(clause);
                    }
                }, this);
            }
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
            var result = this.rootrule.getValue();
            if (result && nested.test(result)) {
                // There will be one extra paren set wrapping the clause as a
                // whole that is hard to prevent earlier than this; don't save
                // it, as it will be treated as an unnecessary nested rule
                result = unparen.exec(result)[1];
            }
            return result;
        },
        setValue: function(expression) {
            if (!expression) {
                this.reset();
            } else {
                this.rootrule.setValue(expression);
            }
            this.doLayout();
        },
        reset: function() {
            this.rootrule.clauses.removeAll();
            this.rootrule.clauses.add({
                xtype: 'ruleclause'
            });
        }
    });

    Ext.reg('rulebuilder', ZF.RuleBuilder);

    ZF.STRINGCOMPARISONS = [
        'contains',
        'doesnotcontain',
        'startswith',
        'doesnotstartwith',
        'endswith',
        'doesnotendwith',
        'equals',
        'doesnotequal'
    ];

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

    ZF.LISTCOMPARISONS = [
        'contains',
        'doesnotcontain'
    ];

    var smarterSetValue = function(val) {
        if (!this.loaded) {
            this.store.load({
                callback: function(){
                    this.loaded = true;
                    Ext.form.ComboBox.prototype.setValue.call(this, val);
                    if (this.taTask) {
                        this.taTask.cancel();
                    }
                    this.collapse();
                },
                scope: this
            });
        } else {
            Ext.form.ComboBox.prototype.setValue.call(this, val);
        }
    };

    var smarterSetIntValue = function(val) {
        val = parseInt(val, 0);
        smarterSetValue.call(this, val);
    };

    Ext.apply(ZF, {
        EVENTSEVERITY: {
            text: _t('Severity'),
            value: 'severity',
            comparisons: ZF.NUMBERCOMPARISONS,
            field: {
                xtype: 'combo',
                mode: 'local',
                valueField: 'value',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                store: new Ext.data.ArrayStore({
                    fields: ['name', 'value'],
                    data: [[
                        _t('Critical'), 5
                    ],[
                        _t('Error'), 4
                    ],[
                        _t('Warning'), 3
                    ],[
                        _t('Info'), 2
                    ],[
                        _t('Debug'), 1
                    ],[
                        _t('Clear'), 0
                    ]]
                })
            }
        },
        PRODUCTIONSTATE: {
            text: _t('Production state'),
            value: 'productionState',
            field: {
                xtype: 'ProductionStateCombo',
                setValue: smarterSetIntValue
            },
            comparisons: ZF.NUMBERCOMPARISONS
        },
        DEVICEPRIORITY: {
            text: _t('Device priority'),
            value: 'priority',
            field: {
                xtype: 'PriorityCombo',
                setValue: smarterSetIntValue
            },
            comparisons: ZF.NUMBERCOMPARISONS
        },
        DEVICE: {
            text: _t('Device'),
            value: 'device_uuid',
            comparisons: ZF.IDENTITYCOMPARISONS,
            field: {
                xtype: 'combo',
                setValue: smarterSetValue,
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
        },
        COMPONENT: {
            text: _t('Component'),
            value: 'component_uuid',
            comparisons: ZF.IDENTITYCOMPARISONS,
            field: {
                xtype: 'combo',
                setValue: smarterSetValue,
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
        },
        DEVICECLASS: {
            text: _t('Device Class'),
            value: 'dev.device_class',
            comparisons: ZF.STRINGCOMPARISONS,
            field: {
                xtype: 'combo',
                setValue: smarterSetValue,
                mode: 'remote',
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getDeviceClasses,
                    root: 'deviceClasses',
                    fields: ['name']
                }),
                typeAhead: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: true,
                triggerAction: 'all'
            }
        },
        SYSTEMS: {
            text: _t('Systems'),
            value: 'dev.systems',
            comparisons: ZF.LISTCOMPARISONS,
            field: {
                xtype: 'combo',
                setValue: smarterSetValue,
                mode: 'remote',
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getSystems,
                    root: 'systems',
                    fields: ['name']
                }),
                typeAhead: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: true,
                triggerAction: 'all'
            }
        },
        DEVICEGROUPS: {
            text: _t('Device Groups'),
            value: 'dev.groups',
            comparisons: ZF.LISTCOMPARISONS,
            field: {
                xtype: 'combo',
                setValue: smarterSetValue,
                mode: 'remote',
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getGroups,
                    root: 'groups',
                    fields: ['name']
                }),
                typeAhead: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: true,
                triggerAction: 'all'
            }
        }
    });

})();
