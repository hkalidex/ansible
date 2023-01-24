<%@ taglib prefix="s" uri="/WEB-INF/struts-tags.tld"%>
   <s:include value="mainTopMini.jsp">
      <s:param name="scripts">
         <script type="text/javascript">
            var isRootPage = true;
         </script>
      </s:param>
      <s:param name="styles">
      <!--- TODO -->
         <link rel="stylesheet" href="extjs5.1/ux/css/CheckHeader.css">
         <style type="text/css">
            .newTab {
               background-image:url(images/tmp/new_tab.gif) !important;
            }

            .intel-nav {
              background-color: #0071C5 !important;
            }

            .intel-logo {
              background-image: url("images/intel/intel_logo_index.png") !important;
              background-size: 100% 100% !important;
              background-repeat: no-repeat;
              width: 65px;
              height: 45px;
              margin-right: 1em;
            }
         </style>
      </s:param>
   </s:include>
   </head>
   <body>
   <script type="text/javascript" src="js/chrome/chrome.js"></script>
   <script type="text/javascript">
      Ext.onReady(function() {
          var splashscreen = Ext.getBody().mask('<div class="splash-screen-container"><div class="splash-screen-logo"></div><div class="splash-screen-message">' +  bundle["main.loadingResources"] + ' </div><div class="progress-bar-container"><div class="splash-spinner"></div></div></div></div>', 'splashscreen');
          Ext.DomHelper.insertFirst(splashscreen, {
             cls: 'splash-screen-background'
          });
          if (Ext.util.Cookies.get('keepSplashscreen') !== "true" ) {
              setTimeout(function () {
                  Ext.getBody().unmask();
              }, 2000);
          }
          var activeTab = parseInt(Ext.History.getToken());
          activeTab = activeTab > 2 || activeTab < 0 ? 0 : activeTab;

          Ext.create('Ext.vcops.Viewport', {
              activeTab: activeTab
          });
      });
    </script>
   </body>
</html>
