<!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
 <title>/trunk/Products/ZenHub/PBDaemon.py - Zenoss - Trac</title><link rel="start" href="/trac/wiki" /><link rel="search" href="/trac/search" /><link rel="help" href="/trac/wiki/TracGuide" /><link rel="stylesheet" href="/trac/chrome/common/css/trac.css" type="text/css" /><link rel="stylesheet" href="/trac/chrome/common/css/code.css" type="text/css" /><link rel="stylesheet" href="/trac/chrome/common/css/browser.css" type="text/css" /><link rel="icon" href="/trac/chrome/common/trac.ico" type="image/x-icon" /><link rel="shortcut icon" href="/trac/chrome/common/trac.ico" type="image/x-icon" /><link rel="up" href="/trac/browser/trunk/Products/ZenHub?rev=8156" title="Parent directory" /><link rel="alternate" href="/trac/browser/trunk/Products/ZenHub/PBDaemon.py?rev=8156&amp;format=txt" title="Plain Text" type="text/plain" /><link rel="alternate" href="/trac/browser/trunk/Products/ZenHub/PBDaemon.py?rev=8156&amp;format=raw" title="Original Format" type="text/x-python; charset=iso-8859-15" /><style type="text/css">

@import url(/trac/chrome/site/local.css);
#header {height: 48px; margin-bottom: -7px !important; width: 100%;}
#header table {margin: 0px 0px 0px 0px; padding: 0px; border: 0px; border-spacing: 0px; width: 100% !important; height: 48px;}

#header td.logo a img {margin: 0 !important;}
.logo {width: 199px; vertical-align: bottom;}

.tagline {
color: #78A0CF;
font-size: 16px;
margin-left: -5px;
vertical-align: middle;
padding-bottom: -5px;
}

td.links {text-align: right; vertical-align: top;}

.links a {
color: #F78B0C; margin-top: 0px; 
}

.links span {
color: #F78B0C;
}

</style>
 <script type="text/javascript" src="/trac/chrome/common/js/trac.js"></script>
</head>
<body>



<div id="topframe">
<div id="header">
    <table cellpadding="0" cellspacing="0" border="0">
      <tbody>
        <tr>
          <td class="logo"><a href="http://www.zenoss.com/"><img
    alt="Zenoss" width="199" height="65" border="0"
    src="http://www.zenoss.com/site-images/onwhitelogo.png" /></a></td>
          <td class="tagline">Open Source IT Monitoring</td>
          <td class="links">
    <a target="_top" href="http://www.zenoss.com/"
       title="Home">Home</a>
      <span>|</span>    
    <a target="_top" href="http://www.zenoss.com/download/"
       title="Download">Download</a>
      <span>|</span>    
    <a target="_top"
       href="http://www.zenoss.com/community/docs"
       title="Docs">Docs</a>
      <span>|</span>    
    <a target="_top" href="http://www.zenoss.com/support"
       title="Support">Support</a>
      <span>|</span>    
    <a target="_top" href="http://www.zenoss.com/buy?c=buy"
       title="Buy">Buy</a>
      <span>|</span>    
    <a target="_top" href="http://blog.zenoss.com"
       title="Blog">Blog</a>
      <span>|</span>    
    <a target="_top" href="http://community.zenoss.com/forums"
       title="Forums">Forums</a>
          </td>
        </tr>
      </tbody>
    </table>

</div>
<div id="banner">

<form id="search" action="/trac/search" method="get">
 <div>
  <label for="proj-search">Search:</label>
  <input type="text" id="proj-search" name="q" size="10" accesskey="f" value="" />
  <input type="submit" value="Search" />
  <input type="hidden" name="wiki" value="on" />
  <input type="hidden" name="changeset" value="on" />
  <input type="hidden" name="ticket" value="on" />
 </div>
</form>



<div id="metanav" class="nav"><ul><li class="first"><a href="/trac/login">Login</a></li><li><a href="/trac/settings">Settings</a></li><li><a accesskey="6" href="/trac/wiki/TracGuide">Help/Guide</a></li><li class="last"><a href="/trac/about">About Trac</a></li></ul></div>
</div>

<div id="mainnav" class="nav"><ul><li class="first"><a accesskey="1" href="/trac/wiki">Wiki</a></li><li><a accesskey="2" href="/trac/timeline">Timeline</a></li><li><a accesskey="3" href="/trac/roadmap">Roadmap</a></li><li class="active"><a href="/trac/browser">Browse Source</a></li><li><a href="/trac/report">View Tickets</a></li><li class="last"><a accesskey="4" href="/trac/search">Search</a></li></ul></div>
<div id="main">




<div id="ctxtnav" class="nav">
 <ul>
  <li class="first"><a href="/trac/changeset/8156/trunk/Products/ZenHub/PBDaemon.py">
   Last Change</a></li>
  <li class="last"><a href="/trac/log/trunk/Products/ZenHub/PBDaemon.py?rev=8156">
   Revision Log</a></li>
 </ul>
</div>


<div id="searchable">
<div id="content" class="browser">
 <h1><a class="first" title="Go to root directory" href="/trac/browser?rev=8156">root</a><span class="sep">/</span><a title="View trunk" href="/trac/browser/trunk?rev=8156">trunk</a><span class="sep">/</span><a title="View Products" href="/trac/browser/trunk/Products?rev=8156">Products</a><span class="sep">/</span><a title="View ZenHub" href="/trac/browser/trunk/Products/ZenHub?rev=8156">ZenHub</a><span class="sep">/</span><a title="View PBDaemon.py" href="/trac/browser/trunk/Products/ZenHub/PBDaemon.py?rev=8156">PBDaemon.py</a></h1>

 <div id="jumprev">
  <form action="" method="get">
   <div>
    <label for="rev">View revision:</label>
    <input type="text" id="rev" name="rev" value="8156" size="4" />
   </div>
  </form>
 </div>

 

 
  <table id="info" summary="Revision info"><tr>
    <th scope="col">
     Revision <a href="/trac/changeset/8156">8156</a>, 10.7 kB
     (checked in by ecn, 1 month ago)
    </th></tr><tr>
    <td class="message"><pre>Merge changes from sandboxen:
 * fixes #2094 convert zenmodeler into a PBDaemon
   - evaluate plugin conditionals in zenhub
   - send plugins with device configuration
   - make object maps and plugin loaders PB-transferable
   - alter zenmodeler to accept the PBDaemon mainloop
   - allow the creation/filter of objects using object maps
   - move ApplyDataMap into ZenHub
</pre></td>
   </tr>
  </table>
  <div id="preview"><table class="code"><thead><tr><th class="lineno">Line</th><th class="content">&nbsp;</th></tr></thead><tbody><tr><th id="L1"><a href="#L1">1</a></th>
<td>###########################################################################</td>
</tr><tr><th id="L2"><a href="#L2">2</a></th>
<td>#</td>
</tr><tr><th id="L3"><a href="#L3">3</a></th>
<td># This program is part of Zenoss Core, an open source monitoring platform.</td>
</tr><tr><th id="L4"><a href="#L4">4</a></th>
<td># Copyright (C) 2007, Zenoss Inc.</td>
</tr><tr><th id="L5"><a href="#L5">5</a></th>
<td>#</td>
</tr><tr><th id="L6"><a href="#L6">6</a></th>
<td># This program is free software; you can redistribute it and/or modify it</td>
</tr><tr><th id="L7"><a href="#L7">7</a></th>
<td># under the terms of the GNU General Public License version 2 as published by</td>
</tr><tr><th id="L8"><a href="#L8">8</a></th>
<td># the Free Software Foundation.</td>
</tr><tr><th id="L9"><a href="#L9">9</a></th>
<td>#</td>
</tr><tr><th id="L10"><a href="#L10">10</a></th>
<td># For complete information please visit: http://www.zenoss.com/oss/</td>
</tr><tr><th id="L11"><a href="#L11">11</a></th>
<td>#</td>
</tr><tr><th id="L12"><a href="#L12">12</a></th>
<td>###########################################################################</td>
</tr><tr><th id="L13"><a href="#L13">13</a></th>
<td></td>
</tr><tr><th id="L14"><a href="#L14">14</a></th>
<td>__doc__='''PBDaemon</td>
</tr><tr><th id="L15"><a href="#L15">15</a></th>
<td></td>
</tr><tr><th id="L16"><a href="#L16">16</a></th>
<td>Base for daemons that connect to zenhub</td>
</tr><tr><th id="L17"><a href="#L17">17</a></th>
<td></td>
</tr><tr><th id="L18"><a href="#L18">18</a></th>
<td>'''</td>
</tr><tr><th id="L19"><a href="#L19">19</a></th>
<td></td>
</tr><tr><th id="L20"><a href="#L20">20</a></th>
<td>import Globals</td>
</tr><tr><th id="L21"><a href="#L21">21</a></th>
<td>from Products.ZenUtils.ZenDaemon import ZenDaemon</td>
</tr><tr><th id="L22"><a href="#L22">22</a></th>
<td>from Products.ZenEvents.ZenEventClasses import Heartbeat</td>
</tr><tr><th id="L23"><a href="#L23">23</a></th>
<td>from Products.ZenUtils.PBUtil import ReconnectingPBClientFactory</td>
</tr><tr><th id="L24"><a href="#L24">24</a></th>
<td>from Products.ZenUtils.DaemonStats import DaemonStats</td>
</tr><tr><th id="L25"><a href="#L25">25</a></th>
<td></td>
</tr><tr><th id="L26"><a href="#L26">26</a></th>
<td>from twisted.internet import reactor, defer</td>
</tr><tr><th id="L27"><a href="#L27">27</a></th>
<td>from twisted.cred import credentials</td>
</tr><tr><th id="L28"><a href="#L28">28</a></th>
<td>from twisted.spread import pb</td>
</tr><tr><th id="L29"><a href="#L29">29</a></th>
<td></td>
</tr><tr><th id="L30"><a href="#L30">30</a></th>
<td>from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop, \</td>
</tr><tr><th id="L31"><a href="#L31">31</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Clear, Warning</td>
</tr><tr><th id="L32"><a href="#L32">32</a></th>
<td></td>
</tr><tr><th id="L33"><a href="#L33">33</a></th>
<td>from socket import getfqdn</td>
</tr><tr><th id="L34"><a href="#L34">34</a></th>
<td></td>
</tr><tr><th id="L35"><a href="#L35">35</a></th>
<td>PB_PORT = 8789</td>
</tr><tr><th id="L36"><a href="#L36">36</a></th>
<td></td>
</tr><tr><th id="L37"><a href="#L37">37</a></th>
<td>startEvent = {</td>
</tr><tr><th id="L38"><a href="#L38">38</a></th>
<td>&nbsp; &nbsp; 'eventClass': App_Start, </td>
</tr><tr><th id="L39"><a href="#L39">39</a></th>
<td>&nbsp; &nbsp; 'summary': 'started',</td>
</tr><tr><th id="L40"><a href="#L40">40</a></th>
<td>&nbsp; &nbsp; 'severity': Clear,</td>
</tr><tr><th id="L41"><a href="#L41">41</a></th>
<td>&nbsp; &nbsp; }</td>
</tr><tr><th id="L42"><a href="#L42">42</a></th>
<td></td>
</tr><tr><th id="L43"><a href="#L43">43</a></th>
<td>stopEvent = {</td>
</tr><tr><th id="L44"><a href="#L44">44</a></th>
<td>&nbsp; &nbsp; 'eventClass':App_Stop, </td>
</tr><tr><th id="L45"><a href="#L45">45</a></th>
<td>&nbsp; &nbsp; 'summary': 'stopped',</td>
</tr><tr><th id="L46"><a href="#L46">46</a></th>
<td>&nbsp; &nbsp; 'severity': Warning,</td>
</tr><tr><th id="L47"><a href="#L47">47</a></th>
<td>&nbsp; &nbsp; }</td>
</tr><tr><th id="L48"><a href="#L48">48</a></th>
<td></td>
</tr><tr><th id="L49"><a href="#L49">49</a></th>
<td></td>
</tr><tr><th id="L50"><a href="#L50">50</a></th>
<td>DEFAULT_HUB_HOST = 'localhost'</td>
</tr><tr><th id="L51"><a href="#L51">51</a></th>
<td>DEFAULT_HUB_PORT = PB_PORT</td>
</tr><tr><th id="L52"><a href="#L52">52</a></th>
<td>DEFAULT_HUB_USERNAME = 'admin'</td>
</tr><tr><th id="L53"><a href="#L53">53</a></th>
<td>DEFAULT_HUB_PASSWORD = 'zenoss'</td>
</tr><tr><th id="L54"><a href="#L54">54</a></th>
<td>DEFAULT_HUB_MONITOR = 'localhost'</td>
</tr><tr><th id="L55"><a href="#L55">55</a></th>
<td></td>
</tr><tr><th id="L56"><a href="#L56">56</a></th>
<td>class HubDown(Exception): pass</td>
</tr><tr><th id="L57"><a href="#L57">57</a></th>
<td></td>
</tr><tr><th id="L58"><a href="#L58">58</a></th>
<td>class FakeRemote:</td>
</tr><tr><th id="L59"><a href="#L59">59</a></th>
<td>&nbsp; &nbsp; def callRemote(self, *unused):</td>
</tr><tr><th id="L60"><a href="#L60">60</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return defer.fail(HubDown(&#34;ZenHub is down&#34;))</td>
</tr><tr><th id="L61"><a href="#L61">61</a></th>
<td></td>
</tr><tr><th id="L62"><a href="#L62">62</a></th>
<td>class PBDaemon(ZenDaemon, pb.Referenceable):</td>
</tr><tr><th id="L63"><a href="#L63">63</a></th>
<td>&nbsp; &nbsp; </td>
</tr><tr><th id="L64"><a href="#L64">64</a></th>
<td>&nbsp; &nbsp; name = 'pbdaemon'</td>
</tr><tr><th id="L65"><a href="#L65">65</a></th>
<td>&nbsp; &nbsp; initialServices = ['EventService']</td>
</tr><tr><th id="L66"><a href="#L66">66</a></th>
<td>&nbsp; &nbsp; heartbeatEvent = {'eventClass':Heartbeat}</td>
</tr><tr><th id="L67"><a href="#L67">67</a></th>
<td>&nbsp; &nbsp; heartbeatTimeout = 60*3</td>
</tr><tr><th id="L68"><a href="#L68">68</a></th>
<td>&nbsp; &nbsp; </td>
</tr><tr><th id="L69"><a href="#L69">69</a></th>
<td>&nbsp; &nbsp; def __init__(self, noopts=0, keeproot=False):</td>
</tr><tr><th id="L70"><a href="#L70">70</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; ZenDaemon.__init__(self, noopts, keeproot)</td>
</tr><tr><th id="L71"><a href="#L71">71</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.rrdStats = DaemonStats()</td>
</tr><tr><th id="L72"><a href="#L72">72</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.perspective = None</td>
</tr><tr><th id="L73"><a href="#L73">73</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.services = {}</td>
</tr><tr><th id="L74"><a href="#L74">74</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.eventQueue = []</td>
</tr><tr><th id="L75"><a href="#L75">75</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.startEvent = startEvent.copy()</td>
</tr><tr><th id="L76"><a href="#L76">76</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.stopEvent = stopEvent.copy()</td>
</tr><tr><th id="L77"><a href="#L77">77</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; details = dict(component=self.name, device=getfqdn())</td>
</tr><tr><th id="L78"><a href="#L78">78</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; for evt in self.startEvent, self.stopEvent, self.heartbeatEvent:</td>
</tr><tr><th id="L79"><a href="#L79">79</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; evt.update(details)</td>
</tr><tr><th id="L80"><a href="#L80">80</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.initialConnect = defer.Deferred()</td>
</tr><tr><th id="L81"><a href="#L81">81</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.stopped = False</td>
</tr><tr><th id="L82"><a href="#L82">82</a></th>
<td></td>
</tr><tr><th id="L83"><a href="#L83">83</a></th>
<td>&nbsp; &nbsp; def gotPerspective(self, perspective):</td>
</tr><tr><th id="L84"><a href="#L84">84</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; ''' This gets called every time we reconnect.</td>
</tr><tr><th id="L85"><a href="#L85">85</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; '''</td>
</tr><tr><th id="L86"><a href="#L86">86</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.warning(&#34;Reconnected to ZenHub&#34;)</td>
</tr><tr><th id="L87"><a href="#L87">87</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.perspective = perspective</td>
</tr><tr><th id="L88"><a href="#L88">88</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d2 = self.getInitialServices()</td>
</tr><tr><th id="L89"><a href="#L89">89</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if self.initialConnect:</td>
</tr><tr><th id="L90"><a href="#L90">90</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('chaining getInitialServices with d2')</td>
</tr><tr><th id="L91"><a href="#L91">91</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.initialConnect, d = None, self.initialConnect</td>
</tr><tr><th id="L92"><a href="#L92">92</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; d2.chainDeferred(d)</td>
</tr><tr><th id="L93"><a href="#L93">93</a></th>
<td></td>
</tr><tr><th id="L94"><a href="#L94">94</a></th>
<td></td>
</tr><tr><th id="L95"><a href="#L95">95</a></th>
<td>&nbsp; &nbsp; def connect(self):</td>
</tr><tr><th id="L96"><a href="#L96">96</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; factory = ReconnectingPBClientFactory()</td>
</tr><tr><th id="L97"><a href="#L97">97</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.debug(&#34;Connecting to %s&#34;, self.options.hubhost)</td>
</tr><tr><th id="L98"><a href="#L98">98</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; reactor.connectTCP(self.options.hubhost, self.options.hubport, factory)</td>
</tr><tr><th id="L99"><a href="#L99">99</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; username = self.options.hubusername</td>
</tr><tr><th id="L100"><a href="#L100">100</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; password = self.options.hubpassword</td>
</tr><tr><th id="L101"><a href="#L101">101</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.debug(&#34;Logging in as %s&#34;, username)</td>
</tr><tr><th id="L102"><a href="#L102">102</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; c = credentials.UsernamePassword(username, password)</td>
</tr><tr><th id="L103"><a href="#L103">103</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; factory.gotPerspective = self.gotPerspective</td>
</tr><tr><th id="L104"><a href="#L104">104</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; factory.startLogin(c)</td>
</tr><tr><th id="L105"><a href="#L105">105</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return self.initialConnect</td>
</tr><tr><th id="L106"><a href="#L106">106</a></th>
<td></td>
</tr><tr><th id="L107"><a href="#L107">107</a></th>
<td></td>
</tr><tr><th id="L108"><a href="#L108">108</a></th>
<td>&nbsp; &nbsp; def eventService(self):</td>
</tr><tr><th id="L109"><a href="#L109">109</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return self.getServiceNow('EventService')</td>
</tr><tr><th id="L110"><a href="#L110">110</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; </td>
</tr><tr><th id="L111"><a href="#L111">111</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; </td>
</tr><tr><th id="L112"><a href="#L112">112</a></th>
<td>&nbsp; &nbsp; def getServiceNow(self, svcName):</td>
</tr><tr><th id="L113"><a href="#L113">113</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if not self.services.has_key(svcName):</td>
</tr><tr><th id="L114"><a href="#L114">114</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.error('getServiceNow returning FakeRemote for %s' % svcName)</td>
</tr><tr><th id="L115"><a href="#L115">115</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return self.services.get(svcName, None) or FakeRemote()</td>
</tr><tr><th id="L116"><a href="#L116">116</a></th>
<td></td>
</tr><tr><th id="L117"><a href="#L117">117</a></th>
<td></td>
</tr><tr><th id="L118"><a href="#L118">118</a></th>
<td>&nbsp; &nbsp; def getService(self, serviceName, serviceListeningInterface=None):</td>
</tr><tr><th id="L119"><a href="#L119">119</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; ''' Attempt to get a service from zenhub.&nbsp; Returns a deferred.</td>
</tr><tr><th id="L120"><a href="#L120">120</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; When service is retrieved it is stashed in self.services with</td>
</tr><tr><th id="L121"><a href="#L121">121</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; serviceName as the key.&nbsp; When getService is called it will first</td>
</tr><tr><th id="L122"><a href="#L122">122</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; check self.services and if serviceName is already there it will return</td>
</tr><tr><th id="L123"><a href="#L123">123</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; the entry from self.services wrapped in a defer.succeed</td>
</tr><tr><th id="L124"><a href="#L124">124</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; '''</td>
</tr><tr><th id="L125"><a href="#L125">125</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if self.services.has_key(serviceName):</td>
</tr><tr><th id="L126"><a href="#L126">126</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; return defer.succeed(self.services[serviceName])</td>
</tr><tr><th id="L127"><a href="#L127">127</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; def removeService(ignored):</td>
</tr><tr><th id="L128"><a href="#L128">128</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('removing service %s' % serviceName)</td>
</tr><tr><th id="L129"><a href="#L129">129</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; if serviceName in self.services:</td>
</tr><tr><th id="L130"><a href="#L130">130</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; del self.services[serviceName]</td>
</tr><tr><th id="L131"><a href="#L131">131</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; def callback(result, serviceName):</td>
</tr><tr><th id="L132"><a href="#L132">132</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('callback after getting service %s' % serviceName)</td>
</tr><tr><th id="L133"><a href="#L133">133</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.services[serviceName] = result</td>
</tr><tr><th id="L134"><a href="#L134">134</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; result.notifyOnDisconnect(removeService)</td>
</tr><tr><th id="L135"><a href="#L135">135</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; return result</td>
</tr><tr><th id="L136"><a href="#L136">136</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; def errback(error, serviceName):</td>
</tr><tr><th id="L137"><a href="#L137">137</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('errback after getting service %s' % serviceName)</td>
</tr><tr><th id="L138"><a href="#L138">138</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.error('Could not retrieve service %s' % serviceName)</td>
</tr><tr><th id="L139"><a href="#L139">139</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; if serviceName in self.service:</td>
</tr><tr><th id="L140"><a href="#L140">140</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; del self.services[serviceName]</td>
</tr><tr><th id="L141"><a href="#L141">141</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; #return error</td>
</tr><tr><th id="L142"><a href="#L142">142</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d = self.perspective.callRemote('getService',</td>
</tr><tr><th id="L143"><a href="#L143">143</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; serviceName,</td>
</tr><tr><th id="L144"><a href="#L144">144</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.options.monitor,</td>
</tr><tr><th id="L145"><a href="#L145">145</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; serviceListeningInterface or self)</td>
</tr><tr><th id="L146"><a href="#L146">146</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d.addCallback(callback, serviceName)</td>
</tr><tr><th id="L147"><a href="#L147">147</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d.addErrback(errback, serviceName)</td>
</tr><tr><th id="L148"><a href="#L148">148</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return d</td>
</tr><tr><th id="L149"><a href="#L149">149</a></th>
<td></td>
</tr><tr><th id="L150"><a href="#L150">150</a></th>
<td>&nbsp; &nbsp; def getInitialServices(self):</td>
</tr><tr><th id="L151"><a href="#L151">151</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('setting up services %s' %</td>
</tr><tr><th id="L152"><a href="#L152">152</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ', '.join([n for n in self.initialServices]))</td>
</tr><tr><th id="L153"><a href="#L153">153</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d = defer.DeferredList(</td>
</tr><tr><th id="L154"><a href="#L154">154</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; [self.getService(name) for name in self.initialServices],</td>
</tr><tr><th id="L155"><a href="#L155">155</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; fireOnOneErrback=True, consumeErrors=True)</td>
</tr><tr><th id="L156"><a href="#L156">156</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return d</td>
</tr><tr><th id="L157"><a href="#L157">157</a></th>
<td></td>
</tr><tr><th id="L158"><a href="#L158">158</a></th>
<td></td>
</tr><tr><th id="L159"><a href="#L159">159</a></th>
<td>&nbsp; &nbsp; def connected(self):</td>
</tr><tr><th id="L160"><a href="#L160">160</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; pass</td>
</tr><tr><th id="L161"><a href="#L161">161</a></th>
<td>&nbsp; &nbsp; </td>
</tr><tr><th id="L162"><a href="#L162">162</a></th>
<td>&nbsp; &nbsp; def run(self):</td>
</tr><tr><th id="L163"><a href="#L163">163</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('run')</td>
</tr><tr><th id="L164"><a href="#L164">164</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d = self.connect()</td>
</tr><tr><th id="L165"><a href="#L165">165</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; def callback(result):</td>
</tr><tr><th id="L166"><a href="#L166">166</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('Calling connected.')</td>
</tr><tr><th id="L167"><a href="#L167">167</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.debug('connected')</td>
</tr><tr><th id="L168"><a href="#L168">168</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.sendEvent(self.startEvent)</td>
</tr><tr><th id="L169"><a href="#L169">169</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.connected()</td>
</tr><tr><th id="L170"><a href="#L170">170</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; return result</td>
</tr><tr><th id="L171"><a href="#L171">171</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; def errback(error):</td>
</tr><tr><th id="L172"><a href="#L172">172</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.error('Unable to connect to zenhub: \n%s' % error)</td>
</tr><tr><th id="L173"><a href="#L173">173</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.stop()</td>
</tr><tr><th id="L174"><a href="#L174">174</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; d.addCallbacks(callback, errback)</td>
</tr><tr><th id="L175"><a href="#L175">175</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; reactor.run()</td>
</tr><tr><th id="L176"><a href="#L176">176</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.info('%s shutting down' % self.name)</td>
</tr><tr><th id="L177"><a href="#L177">177</a></th>
<td></td>
</tr><tr><th id="L178"><a href="#L178">178</a></th>
<td>&nbsp; &nbsp; def sigTerm(self, signum=None, frame=None):</td>
</tr><tr><th id="L179"><a href="#L179">179</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; try:</td>
</tr><tr><th id="L180"><a href="#L180">180</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ZenDaemon.sigTerm(self, signum, frame)</td>
</tr><tr><th id="L181"><a href="#L181">181</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; except SystemExit:</td>
</tr><tr><th id="L182"><a href="#L182">182</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; pass</td>
</tr><tr><th id="L183"><a href="#L183">183</a></th>
<td></td>
</tr><tr><th id="L184"><a href="#L184">184</a></th>
<td>&nbsp; &nbsp; def stop(self):</td>
</tr><tr><th id="L185"><a href="#L185">185</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if reactor.running and not self.stopped:</td>
</tr><tr><th id="L186"><a href="#L186">186</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.stopped = True</td>
</tr><tr><th id="L187"><a href="#L187">187</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; if 'EventService' in self.services:</td>
</tr><tr><th id="L188"><a href="#L188">188</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.sendEvent(self.stopEvent)</td>
</tr><tr><th id="L189"><a href="#L189">189</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # give the reactor some time to send the shutdown event</td>
</tr><tr><th id="L190"><a href="#L190">190</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # we could get more creative an add callbacks for event</td>
</tr><tr><th id="L191"><a href="#L191">191</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # sends, which would mean we could wait longer, only as long</td>
</tr><tr><th id="L192"><a href="#L192">192</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # as it took to send</td>
</tr><tr><th id="L193"><a href="#L193">193</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; reactor.callLater(1, reactor.stop)</td>
</tr><tr><th id="L194"><a href="#L194">194</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; else:</td>
</tr><tr><th id="L195"><a href="#L195">195</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; reactor.stop()</td>
</tr><tr><th id="L196"><a href="#L196">196</a></th>
<td></td>
</tr><tr><th id="L197"><a href="#L197">197</a></th>
<td>&nbsp; &nbsp; def sendEvents(self, events):</td>
</tr><tr><th id="L198"><a href="#L198">198</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; map(self.sendEvent, events)</td>
</tr><tr><th id="L199"><a href="#L199">199</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; </td>
</tr><tr><th id="L200"><a href="#L200">200</a></th>
<td>&nbsp; &nbsp; def sendEvent(self, event, **kw):</td>
</tr><tr><th id="L201"><a href="#L201">201</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; ''' Add event to queue of events to be sent.&nbsp; If we have an event</td>
</tr><tr><th id="L202"><a href="#L202">202</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; service then process the queue.</td>
</tr><tr><th id="L203"><a href="#L203">203</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; '''</td>
</tr><tr><th id="L204"><a href="#L204">204</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if not reactor.running: return</td>
</tr><tr><th id="L205"><a href="#L205">205</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; event = event.copy()</td>
</tr><tr><th id="L206"><a href="#L206">206</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; event['agent'] = self.name</td>
</tr><tr><th id="L207"><a href="#L207">207</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; event['manager'] = self.options.monitor</td>
</tr><tr><th id="L208"><a href="#L208">208</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; event.update(kw)</td>
</tr><tr><th id="L209"><a href="#L209">209</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.debug(&#34;Sending event %r&#34;, event)</td>
</tr><tr><th id="L210"><a href="#L210">210</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; def errback(error, event):</td>
</tr><tr><th id="L211"><a href="#L211">211</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # If we get an error when sending an event we add it back to the </td>
</tr><tr><th id="L212"><a href="#L212">212</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # queue.&nbsp; This is great if the eventservice is just temporarily</td>
</tr><tr><th id="L213"><a href="#L213">213</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # unavailable.&nbsp; This is not so good if there is a problem with</td>
</tr><tr><th id="L214"><a href="#L214">214</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # this event in particular, in which case we'll repeatedly </td>
</tr><tr><th id="L215"><a href="#L215">215</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # attempt to send it.&nbsp; We need to do some analysis of the error</td>
</tr><tr><th id="L216"><a href="#L216">216</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # before sticking event back in the queue.</td>
</tr><tr><th id="L217"><a href="#L217">217</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; #</td>
</tr><tr><th id="L218"><a href="#L218">218</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # Maybe this is overkill and if we have an operable</td>
</tr><tr><th id="L219"><a href="#L219">219</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # event service we should just log events that don't get sent</td>
</tr><tr><th id="L220"><a href="#L220">220</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # and then drop them.</td>
</tr><tr><th id="L221"><a href="#L221">221</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; if reactor.running:</td>
</tr><tr><th id="L222"><a href="#L222">222</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.error('Error sending event: %s' % error)</td>
</tr><tr><th id="L223"><a href="#L223">223</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.eventQueue.append(event)</td>
</tr><tr><th id="L224"><a href="#L224">224</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if event:</td>
</tr><tr><th id="L225"><a href="#L225">225</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.eventQueue.append(event)</td>
</tr><tr><th id="L226"><a href="#L226">226</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; evtSvc = self.services.get('EventService', None)</td>
</tr><tr><th id="L227"><a href="#L227">227</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if evtSvc:</td>
</tr><tr><th id="L228"><a href="#L228">228</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; for i in range(len(self.eventQueue)):</td>
</tr><tr><th id="L229"><a href="#L229">229</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; event = self.eventQueue[0]</td>
</tr><tr><th id="L230"><a href="#L230">230</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; del self.eventQueue[0]</td>
</tr><tr><th id="L231"><a href="#L231">231</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; d = evtSvc.callRemote('sendEvent', event)</td>
</tr><tr><th id="L232"><a href="#L232">232</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; d.addErrback(errback, event)</td>
</tr><tr><th id="L233"><a href="#L233">233</a></th>
<td></td>
</tr><tr><th id="L234"><a href="#L234">234</a></th>
<td></td>
</tr><tr><th id="L235"><a href="#L235">235</a></th>
<td>&nbsp; &nbsp; def heartbeat(self):</td>
</tr><tr><th id="L236"><a href="#L236">236</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; 'if cycling, send a heartbeat, else, shutdown'</td>
</tr><tr><th id="L237"><a href="#L237">237</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; if not self.options.cycle:</td>
</tr><tr><th id="L238"><a href="#L238">238</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.stop()</td>
</tr><tr><th id="L239"><a href="#L239">239</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; return</td>
</tr><tr><th id="L240"><a href="#L240">240</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.sendEvent(self.heartbeatEvent, timeout=self.heartbeatTimeout)</td>
</tr><tr><th id="L241"><a href="#L241">241</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; # heartbeat is normally 3x cycle time</td>
</tr><tr><th id="L242"><a href="#L242">242</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.niceDoggie(self.heartbeatTimeout / 3)</td>
</tr><tr><th id="L243"><a href="#L243">243</a></th>
<td></td>
</tr><tr><th id="L244"><a href="#L244">244</a></th>
<td></td>
</tr><tr><th id="L245"><a href="#L245">245</a></th>
<td>&nbsp; &nbsp; def remote_getName(self):</td>
</tr><tr><th id="L246"><a href="#L246">246</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; return self.name</td>
</tr><tr><th id="L247"><a href="#L247">247</a></th>
<td></td>
</tr><tr><th id="L248"><a href="#L248">248</a></th>
<td></td>
</tr><tr><th id="L249"><a href="#L249">249</a></th>
<td>&nbsp; &nbsp; def remote_shutdown(self, unused):</td>
</tr><tr><th id="L250"><a href="#L250">250</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.stop()</td>
</tr><tr><th id="L251"><a href="#L251">251</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.sigTerm()</td>
</tr><tr><th id="L252"><a href="#L252">252</a></th>
<td></td>
</tr><tr><th id="L253"><a href="#L253">253</a></th>
<td></td>
</tr><tr><th id="L254"><a href="#L254">254</a></th>
<td>&nbsp; &nbsp; def remote_updateThresholdClasses(self, classes):</td>
</tr><tr><th id="L255"><a href="#L255">255</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; from Products.ZenUtils.Utils import importClass</td>
</tr><tr><th id="L256"><a href="#L256">256</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.log.debug(&#34;Loading classes %s&#34;, classes)</td>
</tr><tr><th id="L257"><a href="#L257">257</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; for c in classes:</td>
</tr><tr><th id="L258"><a href="#L258">258</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; try:</td>
</tr><tr><th id="L259"><a href="#L259">259</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; importClass(c)</td>
</tr><tr><th id="L260"><a href="#L260">260</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; except ImportError:</td>
</tr><tr><th id="L261"><a href="#L261">261</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; self.log.exception(&#34;Unable to import class %s&#34;, c)</td>
</tr><tr><th id="L262"><a href="#L262">262</a></th>
<td></td>
</tr><tr><th id="L263"><a href="#L263">263</a></th>
<td>&nbsp; &nbsp; def buildOptions(self):</td>
</tr><tr><th id="L264"><a href="#L264">264</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.parser.add_option('--hub-host',</td>
</tr><tr><th id="L265"><a href="#L265">265</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; dest='hubhost',</td>
</tr><tr><th id="L266"><a href="#L266">266</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; default=DEFAULT_HUB_HOST,</td>
</tr><tr><th id="L267"><a href="#L267">267</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; help='Host of zenhub daemon.'</td>
</tr><tr><th id="L268"><a href="#L268">268</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ' Default is %s.' % DEFAULT_HUB_HOST)</td>
</tr><tr><th id="L269"><a href="#L269">269</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.parser.add_option('--hub-port',</td>
</tr><tr><th id="L270"><a href="#L270">270</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; dest='hubport',</td>
</tr><tr><th id="L271"><a href="#L271">271</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; default=DEFAULT_HUB_PORT,</td>
</tr><tr><th id="L272"><a href="#L272">272</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; help='Port zenhub listens on.'</td>
</tr><tr><th id="L273"><a href="#L273">273</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; 'Default is %s.' % DEFAULT_HUB_PORT)</td>
</tr><tr><th id="L274"><a href="#L274">274</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.parser.add_option('--hub-username',</td>
</tr><tr><th id="L275"><a href="#L275">275</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; dest='hubusername',</td>
</tr><tr><th id="L276"><a href="#L276">276</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; default=DEFAULT_HUB_USERNAME,</td>
</tr><tr><th id="L277"><a href="#L277">277</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; help='Username for zenhub login.'</td>
</tr><tr><th id="L278"><a href="#L278">278</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ' Default is %s.' % DEFAULT_HUB_USERNAME)</td>
</tr><tr><th id="L279"><a href="#L279">279</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.parser.add_option('--hub-password',</td>
</tr><tr><th id="L280"><a href="#L280">280</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; dest='hubpassword',</td>
</tr><tr><th id="L281"><a href="#L281">281</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; default=DEFAULT_HUB_PASSWORD,</td>
</tr><tr><th id="L282"><a href="#L282">282</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; help='Password for zenhub login.'</td>
</tr><tr><th id="L283"><a href="#L283">283</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ' Default is %s.' % DEFAULT_HUB_PASSWORD)</td>
</tr><tr><th id="L284"><a href="#L284">284</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; self.parser.add_option('--monitor', </td>
</tr><tr><th id="L285"><a href="#L285">285</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; dest='monitor',</td>
</tr><tr><th id="L286"><a href="#L286">286</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; default=DEFAULT_HUB_MONITOR,</td>
</tr><tr><th id="L287"><a href="#L287">287</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; help='Name of monitor instance to use for'</td>
</tr><tr><th id="L288"><a href="#L288">288</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ' configuration.&nbsp; Default is %s.'</td>
</tr><tr><th id="L289"><a href="#L289">289</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; % DEFAULT_HUB_MONITOR)</td>
</tr><tr><th id="L290"><a href="#L290">290</a></th>
<td></td>
</tr><tr><th id="L291"><a href="#L291">291</a></th>
<td>&nbsp; &nbsp; &nbsp; &nbsp; ZenDaemon.buildOptions(self)</td>
</tr><tr><th id="L292"><a href="#L292">292</a></th>
<td></td>
</tr></tbody></table>
  </div>

 <div id="help">
  <strong>Note:</strong> See <a href="/trac/wiki/TracBrowser">TracBrowser</a> for help on using the browser.
 </div>

  <div id="anydiff">
   <form action="/trac/anydiff" method="get">
    <div class="buttons">
     <input type="hidden" name="new_path" value="/trunk/Products/ZenHub/PBDaemon.py" />
     <input type="hidden" name="old_path" value="/trunk/Products/ZenHub/PBDaemon.py" />
     <input type="hidden" name="new_rev" value="8156" />
     <input type="hidden" name="old_rev" value="8156" />
     <input type="submit" value="View changes..." title="Prepare an Arbitrary Diff" />
    </div>
   </form>
  </div>

</div>
</div>
<script type="text/javascript">searchHighlight()</script>
<div id="altlinks"><h3>Download in other formats:</h3><ul><li class="first"><a href="/trac/browser/trunk/Products/ZenHub/PBDaemon.py?rev=8156&amp;format=txt">Plain Text</a></li><li class="last"><a href="/trac/browser/trunk/Products/ZenHub/PBDaemon.py?rev=8156&amp;format=raw">Original Format</a></li></ul></div>

</div>

<div id="footer">
 <hr />
 <a id="tracpowered" href="http://trac.edgewall.org/"><img src="/trac/chrome/common/trac_logo_mini.png" height="30" width="107"
   alt="Trac Powered"/></a>
 <p class="left">
  Powered by <a href="/trac/about"><strong>Trac 0.10.4</strong></a><br />
  By <a href="http://www.edgewall.org/">Edgewall Software</a>.
 </p>
 <p class="right">
  Visit the Trac open source project at<br /><a href="http://trac.edgewall.com/">http://trac.edgewall.com/</a>
 </p>
</div>


<!-- Loopfuse analytics code, updated 09/19/2007, shuckins: -->
<script src="http://loopfuse.net/webrecorder/js/listen.js" type="text/javascript"></script>
<script type="text/javascript">
_lf_cid = "zenoss";
_lf_remora();
</script>
<!-- END Loopfuse analytics code: -->

 </body>
</html>

