/**
 * Copyright 2013 VMware, Inc. All rights reserved. -- VMware Confidential
 */
Ext.define('Ext.vcops.Viewport', {

    extend : 'Ext.container.Viewport',

    requires: [
        'Ext.vcops.chrome.DocCenter',
        'Ext.vcops.clarity.NavLink'
    ],

    initMembers : function() {
        var me = this;
        this.navigationPanel = Ext.create('Ext.vcops.AdminNavigationPanel', {
            region : 'west',
            collapsible : true,
            header : false,
            collapsedCls : 'collapsed-navigation-panel',
            dockedItems : Ext.create('widget.container', {
                layout : 'hbox',
                border : false,
                height : 36,
                padding : '10 5 0 5',
                items : [ {
                    xtype: 'component',
                    flex: 1
                }, {
                    xtype: 'tool',
                    type: 'left',
                    scope: this,
                    margin: '5 0 0 0',
                    handler: function () {
                        this.navigationPanel.collapse();
                    }
                } ]
            }),
            padding : 0,
            animCollapse : true,
            split : true,
            border : false,
            bodyBorder : false,
            width : 250,
            listeners : {
                scope : this,
                itemSelected : function(itemId) {
                    this.contentPanel.getLayout().setActiveItem(itemId);
                    this.titleLabel.setText(bundle[itemId + '.title']);
                    if (!showHelpLink) {
                        return;
                    }
                    if (itemId == "support") {
                        Ext.getCmp('helpImg_' + this.ns).setVisible(false);
                    } else {
                        Ext.getCmp('helpImg_' + this.ns).setVisible(true);
                    }
                }
            }
        });

        this.slicesPanel = Ext.create('Ext.vcops.clusterManagement.SlicesPanel', {
            itemId : 'statusAndTroubleshooting',
            listeners : {
                scope : this,
                wizardConfigCompleted : this.wizardConfigCompleted
            }
        });

        this.content = Ext.create('Ext.vcops.softwareUpdates.Content', {
            itemId : 'softwareUpdates',
            border : false
        });

        this.supportPanel = Ext.create('Ext.vcops.support.SupportPanel', {
            itemId : 'support',
            border : false
        });

        this.contentPanel = new Ext.Panel({
            padding : 0,
            region : "center",
            layout : 'card',
            header : false,
            border : false,
            bodyBorder : false,
            split : true,
            dockedItems : this.createHeader(),
            items : [ this.slicesPanel, this.content, this.supportPanel ]
        });

        // var brandingHTML =
        //     "<div class='nav-link'>" +
        //         "<span class='clr-icon clr-vmw-logo'></span>" +
        //         "<span class='title'>"+ bundle['product.productName'] +
        //         "</span>"+
        //     "</div>";

        var brandingHTML =
            "<div class='nav-link'>" +
                "<span class='intel-logo clr-vmw-logo'></span>"+
                // "<span class='intel-logo clr-icon clr-vmw-logo'></span>"+
                "<span class='title'>Intel Cloud Infrastructure Health Manager</span>"+
            "</div>";

        var headerNav = Ext.create('Ext.panel.Panel', {
            flex: 1,
            border: false
        });

        this.items = {
            dockedItems : [{
                dock : 'top',
                xtype : 'container',
                componentCls : 'intel-nav header header-6',
                border : false,
                layout : {
                    type : 'hbox'
                },
                items : [{
                    componentCls : 'branding',
                    id: 'top_level_branding',
                    xtype : 'component',
                    // Do not remove build number for vRAO Instance if one is available
                    // If this is a vRAO instance, display the AIR product name. Also use the AIR buildNumber if it is present.
                    html : brandingHTML,
                    style : {
                        cursor : 'pointer'
                    },
                    listeners : {
                        scope: this,
                        render : function(c) {
                            c.getEl().on({
                                click : function() {
                                    me.navigationPanel.homeButtonClicked(arguments);
                                }
                            });
                        }
                    }
                }, headerNav, {
                    xtype: 'toolbar',
                    baseCls : 'header-nav',
                    items: [{
                        xtype : 'navlink',
                        id: 'top_level_action_refresh',
                        icon: 'themes/clarity-light/images/clarity/header/refresh.svg',
                        listeners:{
                            click: function(cmp) {
                                messageBus.fireEvent('globalrefresh');
                            }
                        }
                    }, {
                        tooltip : bundle['main.certificate'],
                        xtype : 'navlink',
                        icon: 'themes/clarity-light/images/clarity/header/certificate.svg',
                        id: 'top_level_notifications_icon',
                        listeners: {
                            click: function(cmp) {
                                me.setLoading(true);
                                Ext.Ajax.request({
                                    url : 'clusterManagement.action',
                                    params : {
                                        mainAction : 'isPakInstalling'
                                    },
                                    disableCaching : true,
                                    scope : this,
                                    method : 'POST',
                                    success : function(response, options) {
                                        me.setLoading(false);
                                        var data = Ext.JSON.decode(response.responseText, true);

                                        if (!data || (data && data.isPakInstalling)) {
                                            Ext.MessageBox.alert(bundle['main.msg.warning'], bundle['certificate.new.disabled']);
                                        } else {
                                            Ext.create('Ext.vcops.certificate.SslCertificateWindow').show();
                                        }
                                    },
                                    failure : function(response, options) {
                                        me.setLoading(false);
                                        Ext.MessageBox.alert(bundle['main.msg.warning'], bundle['software.restarting']);
                                    }
                                });
                            }
                        }
                    }, {
                        xtype: 'navlink',
                        icon: 'themes/clarity-light/images/clarity/header/user.svg',
                        menu: {
                            plain: true,
                            cls: "userPreferencesMenu",
                            alignOffset: [0, -10],
                            items: [{
                                text: "<span style='font-weight:bold;'>" + bundle['admin.title'] + "</span>",
                            }, {
                                id : 'top_level_action_user_changepassword',
                                disabled : !isLoggedIn,
                                text: bundle['main.changepassword'],
                                handler: function() {
                                    Ext.create('Ext.vcops.main.ChangePasswordWindow').show();
                                }
                            }, '-', {
                                id : 'top_level_action_user_logout',
                                disabled : !isLoggedIn,
                                text: bundle['main.logout'],
                                handler: function() {
                                    window.location.assign('login.action?mainAction=logout');
                                }
                            }]
                        }
                    }]
                }]
            }],
            baseCls : 'app-wrap',
            componentCls : 'app',
            layout : 'fit',
            border : false,
            items : {
                xtype : 'container',
                layout : 'fit',
                border : false,
                items : {
                    xtype : 'container',
                    layout : 'border',
                    border : false,
                    items : [ this.navigationPanel, this.contentPanel ]
                }
            }
        };
    },

    wizardConfigCompleted : function(wizardConfigCompleted) {
        this.navigationPanel.setItemDisabled('softwareUpdates', !wizardConfigCompleted);
        if (!wizardConfigCompleted && this.content.isVisible()) {
            this.contentPanel.getLayout().setActiveItem('statusAndTroubleshooting');
            this.titleLabel.setText(bundle['statusAndTroubleshooting.title']);
            this.navigationPanel.setItemSelected('statusAndTroubleshooting');
        }

        this.enableAdminButtons(wizardConfigCompleted);
    },

    /**
     * enable/disable admin user buttons if the user is not manually logged in (after installation wizard the user is auto logged in)
     * @param enable
     */
    enableAdminButtons : function(enable) {
        if (!isLoggedIn) {
            Ext.getCmp('top_level_action_user_changepassword').setDisabled(!enable);
            Ext.getCmp('top_level_action_user_logout').setDisabled(!enable);
        }
    },

    createHeader : function() {
        this.titleLabel = Ext.create('widget.tbtext', {
            componentCls : 'content-header-label',
            text : bundle['statusAndTroubleshooting.title'],
            padding : '15 5 0 5',
            height : 44
        });

        this.help = Ext.create('Ext.Img', {
            id: "helpImg_" + this.ns,
            src: 'images/common/help.png',
            hidden: !showHelpLink,
            margin: '5 5 0 0',
            width: 16,
            height: 16
        });

        this.help.on({
            scope: this,
            click: {
                element: 'el',
                fn: function() {
                    var activeItemId = this.contentPanel.getLayout().getActiveItem().itemId;
                    var topic = docCenterKeys['content.' + activeItemId];
                    if (topic) {
                        Ext.vcops.chrome.DocCenter.loadByKey(topic);
                    }
                }
            }
        });

        return Ext.create('widget.container', {
            layout : {
                type : 'hbox'
            },
            border : false,
            height : 44,
            items : [ this.titleLabel,
                      {xtype : 'tbspacer', flex : 1},
                      this.help
            ]
        });
    },

    renderMembers : function() {
        var activeItem = 'statusAndTroubleshooting';
        if (this.activeTab == 1) {
            activeItem = 'softwareUpdates';
        } else if (this.activeTab == 2) {
            activeItem = 'support';
        }
        this.contentPanel.getLayout().setActiveItem(activeItem);
        this.titleLabel.setText(bundle[activeItem + '.title']);
        this.navigationPanel.setItemSelected(activeItem);
    },

    initComponent : function() {
        Ext.vcops.chrome.DocCenter.baseUrl = docCenterBaseUrl;
        Ext.vcops.chrome.DocCenter.videoBaseUrl = videoBaseUrl;
        Ext.vcops.chrome.DocCenter.brightcovePlaylistBaseUrl = brightcovePlaylistBaseUrl;
        this.initMembers();
        this.on('afterrender', this.renderMembers);
        var config = {
            border : false,
            layout : 'fit'
        };

        Ext.apply(this, Ext.apply(config, this.initialConfig));
        Ext.vcops.Viewport.superclass.initComponent.apply(this, arguments);
    }
});
