
"""
Copyright 2006 ThoughtWorks, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
__docformat__ = "restructuredtext en"

# This file has been automatically generated via XSL

import httplib
import urllib
import re

class selenium:
    """
Defines an object that runs Selenium commands.
    
    Element Locators
    ~~~~~~~~~~~~~~~~
    Element Locators tell Selenium which HTML element a command refers to.
    The format of a locator is:
    \ *locatorType*\ **=**\ \ *argument*
    We support the following strategies for locating elements:
    
    *    \ **identifier**\ =\ *id*
        Select the element with the specified @id attribute. If no match is
        found, select the first element whose @name attribute is \ *id*.
        (This is normally the default; see below.)
    *    \ **id**\ =\ *id*
        Select the element with the specified @id attribute.
    *    \ **name**\ =\ *name*
        Select the first element with the specified @name attribute.
    
        *    username
        *    name=username
        
        
    
        The name may optionally be followed by one or more \ *element-filters*, separated from the name by whitespace.  If the \ *filterType* is not specified, \ **value**\  is assumed.
    
        *    name=flavour value=chocolate
        
        
    *    \ **dom**\ =\ *javascriptExpression*
        
            Find an element by evaluating the specified string.  This allows you to traverse the HTML Document Object
            Model using JavaScript.  Note that you must not return a value in this string; simply make it the last expression in the block.
            *    dom=document.forms['myForm'].myDropdown
            *    dom=document.images[56]
            *    dom=function foo() { return document.links[1]; }; foo();
            
            
        
    *    \ **xpath**\ =\ *xpathExpression*
        Locate an element using an XPath expression.
        *    xpath=//img[@alt='The image alt text']
        *    xpath=//table[@id='table1']//tr[4]/td[2]
        
        
    *    \ **link**\ =\ *textPattern*
        Select the link (anchor) element which contains text matching the
        specified \ *pattern*.
        *    link=The link text
        
        
    *    \ **css**\ =\ *cssSelectorSyntax*
        Select the element using css selectors. Please refer to CSS2 selectors, CSS3 selectors for more information. You can also check the TestCssLocators test in the selenium test suite for an example of usage, which is included in the downloaded selenium core package.
        *    css=a[href="#id3"]
        *    css=span#firstChild + span
        
        
    
        Currently the css selector locator supports all css1, css2 and css3 selectors except namespace in css3, some pseudo classes(:nth-of-type, :nth-last-of-type, :first-of-type, :last-of-type, :only-of-type, :visited, :hover, :active, :focus, :indeterminate) and pseudo elements(::first-line, ::first-letter, ::selection, ::before, ::after). 
    
    
    Without an explicit locator prefix, Selenium uses the following default
    strategies:
    
    *    \ **dom**\ , for locators starting with "document."
    *    \ **xpath**\ , for locators starting with "//"
    *    \ **identifier**\ , otherwise
    
    Element Filters
    ~~~~~~~~~~~~~~~Element filters can be used with a locator to refine a list of candidate elements.  They are currently used only in the 'name' element-locator.
    Filters look much like locators, ie.
    \ *filterType*\ **=**\ \ *argument*Supported element-filters are:
    \ **value=**\ \ *valuePattern*
    
    Matches elements based on their values.  This is particularly useful for refining a list of similarly-named toggle-buttons.\ **index=**\ \ *index*
    
    Selects a single element based on its position in the list (offset from zero).String-match Patterns
    ~~~~~~~~~~~~~~~~~~~~~
    Various Pattern syntaxes are available for matching string values:
    
    *    \ **glob:**\ \ *pattern*
        Match a string against a "glob" (aka "wildmat") pattern. "Glob" is a
        kind of limited regular-expression syntax typically used in command-line
        shells. In a glob pattern, "*" represents any sequence of characters, and "?"
        represents any single character. Glob patterns match against the entire
        string.
    *    \ **regexp:**\ \ *regexp*
        Match a string using a regular-expression. The full power of JavaScript
        regular-expressions is available.
    *    \ **exact:**\ \ *string*
        Match a string exactly, verbatim, without any of that fancy wildcard
        stuff.
    
    
    If no pattern prefix is specified, Selenium assumes that it's a "glob"
    pattern.
    
    
    """

### This part is hard-coded in the XSL
    def __init__(self, host, port, browserStartCommand, browserURL):
        self.host = host
        self.port = port
        self.browserStartCommand = browserStartCommand
        self.browserURL = browserURL
        self.sessionId = None

    def start(self):
        result = self.get_string("getNewBrowserSession", [self.browserStartCommand, self.browserURL])
        try:
            self.sessionId = long(result)
        except ValueError:
            raise Exception, result
        
    def stop(self):
        self.do_command("testComplete", [])
        self.sessionId = None

    def do_command(self, verb, args):
        conn = httplib.HTTPConnection(self.host, self.port)
        commandString = u'/selenium-server/driver/?cmd=' + urllib.quote_plus(unicode(verb).encode('utf-8'))
        for i in range(len(args)):
            commandString = commandString + '&' + unicode(i+1) + '=' + urllib.quote_plus(unicode(args[i]).encode('utf-8'))
        if (None != self.sessionId):
            commandString = commandString + "&sessionId=" + unicode(self.sessionId)
        conn.request("GET", commandString)
    
        response = conn.getresponse()
        #print response.status, response.reason
        data = unicode(response.read(), "UTF-8")
        result = response.reason
        #print "Selenium Result: " + repr(data) + "\n\n"
        if (not data.startswith('OK')):
            raise Exception, data
        return data
    
    def get_string(self, verb, args):
        result = self.do_command(verb, args)
        return result[3:]
    
    def get_string_array(self, verb, args):
        csv = self.get_string(verb, args)
        token = ""
        tokens = []
        escape = False
        for i in range(len(csv)):
            letter = csv[i]
            if (escape):
                token = token + letter
                escape = False
                continue
            if (letter == '\\'):
                escape = True
            elif (letter == ','):
                tokens.append(token)
                token = ""
            else:
                token = token + letter
        tokens.append(token)
        return tokens

    def get_number(self, verb, args):
        # Is there something I need to do here?
        return self.get_string(verb, args)
    
    def get_number_array(self, verb, args):
        # Is there something I need to do here?
        return self.get_string_array(verb, args)

    def get_boolean(self, verb, args):
        boolstr = self.get_string(verb, args)
        if ("true" == boolstr):
            return True
        if ("false" == boolstr):
            return False
        raise ValueError, "result is neither 'true' nor 'false': " + boolstr
    
    def get_boolean_array(self, verb, args):
        boolarr = self.get_string_array(verb, args)
        for i in range(len(boolarr)):
            if ("true" == boolstr):
                boolarr[i] = True
                continue
            if ("false" == boolstr):
                boolarr[i] = False
                continue
            raise ValueError, "result is neither 'true' nor 'false': " + boolarr[i]
        return boolarr
    
    

### From here on, everything's auto-generated from XML


    def click(self,locator):
        """
        Clicks on a link, button, checkbox or radio button. If the click action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        """
        self.do_command("click", [locator,])


    def double_click(self,locator):
        """
        Double clicks on a link, button, checkbox or radio button. If the double click action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        """
        self.do_command("doubleClick", [locator,])


    def click_at(self,locator,coordString):
        """
        Clicks on a link, button, checkbox or radio button. If the click action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("clickAt", [locator,coordString,])


    def double_click_at(self,locator,coordString):
        """
        Doubleclicks on a link, button, checkbox or radio button. If the action
        causes a new page to load (like a link usually does), call
        waitForPageToLoad.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("doubleClickAt", [locator,coordString,])


    def fire_event(self,locator,eventName):
        """
        Explicitly simulate an event, to trigger the corresponding "on\ *event*"
        handler.
        
        'locator' is an element locator
        'eventName' is the event name, e.g. "focus" or "blur"
        """
        self.do_command("fireEvent", [locator,eventName,])


    def key_press(self,locator,keySequence):
        """
        Simulates a user pressing and releasing a key.
        
        'locator' is an element locator
        'keySequence' is Either be a string("\" followed by the numeric keycode  of the key to be pressed, normally the ASCII value of that key), or a single  character. For example: "w", "\119".
        """
        self.do_command("keyPress", [locator,keySequence,])


    def shift_key_down(self):
        """
        Press the shift key and hold it down until doShiftUp() is called or a new page is loaded.
        
        """
        self.do_command("shiftKeyDown", [])


    def shift_key_up(self):
        """
        Release the shift key.
        
        """
        self.do_command("shiftKeyUp", [])


    def meta_key_down(self):
        """
        Press the meta key and hold it down until doMetaUp() is called or a new page is loaded.
        
        """
        self.do_command("metaKeyDown", [])


    def meta_key_up(self):
        """
        Release the meta key.
        
        """
        self.do_command("metaKeyUp", [])


    def alt_key_down(self):
        """
        Press the alt key and hold it down until doAltUp() is called or a new page is loaded.
        
        """
        self.do_command("altKeyDown", [])


    def alt_key_up(self):
        """
        Release the alt key.
        
        """
        self.do_command("altKeyUp", [])


    def control_key_down(self):
        """
        Press the control key and hold it down until doControlUp() is called or a new page is loaded.
        
        """
        self.do_command("controlKeyDown", [])


    def control_key_up(self):
        """
        Release the control key.
        
        """
        self.do_command("controlKeyUp", [])


    def key_down(self,locator,keySequence):
        """
        Simulates a user pressing a key (without releasing it yet).
        
        'locator' is an element locator
        'keySequence' is Either be a string("\" followed by the numeric keycode  of the key to be pressed, normally the ASCII value of that key), or a single  character. For example: "w", "\119".
        """
        self.do_command("keyDown", [locator,keySequence,])


    def key_up(self,locator,keySequence):
        """
        Simulates a user releasing a key.
        
        'locator' is an element locator
        'keySequence' is Either be a string("\" followed by the numeric keycode  of the key to be pressed, normally the ASCII value of that key), or a single  character. For example: "w", "\119".
        """
        self.do_command("keyUp", [locator,keySequence,])


    def mouse_over(self,locator):
        """
        Simulates a user hovering a mouse over the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseOver", [locator,])


    def mouse_out(self,locator):
        """
        Simulates a user moving the mouse pointer away from the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseOut", [locator,])


    def mouse_down(self,locator):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseDown", [locator,])


    def mouse_down_at(self,locator,coordString):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseDownAt", [locator,coordString,])


    def mouse_up(self,locator):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseUp", [locator,])


    def mouse_up_at(self,locator,coordString):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseUpAt", [locator,coordString,])


    def mouse_move(self,locator):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        """
        self.do_command("mouseMove", [locator,])


    def mouse_move_at(self,locator,coordString):
        """
        Simulates a user pressing the mouse button (without releasing it yet) on
        the specified element.
        
        'locator' is an element locator
        'coordString' is specifies the x,y position (i.e. - 10,20) of the mouse      event relative to the element returned by the locator.
        """
        self.do_command("mouseMoveAt", [locator,coordString,])


    def type(self,locator,value):
        """
        Sets the value of an input field, as though you typed it in.
        
        Can also be used to set the value of combo boxes, check boxes, etc. In these cases,
        value should be the value of the option selected, not the visible text.
        
        
        'locator' is an element locator
        'value' is the value to type
        """
        self.do_command("type", [locator,value,])


    def set_speed(self,value):
        """
        Set execution speed (i.e., set the millisecond length of a delay which will follow each selenium operation).  By default, there is no such delay, i.e.,
        the delay is 0 milliseconds.
        
        'value' is the number of milliseconds to pause after operation
        """
        self.do_command("setSpeed", [value,])


    def get_speed(self):
        """
        Get execution speed (i.e., get the millisecond length of the delay following each selenium operation).  By default, there is no such delay, i.e.,
        the delay is 0 milliseconds.
        
        See also setSpeed.
        
        """
        self.do_command("getSpeed", [])


    def check(self,locator):
        """
        Check a toggle-button (checkbox/radio)
        
        'locator' is an element locator
        """
        self.do_command("check", [locator,])


    def uncheck(self,locator):
        """
        Uncheck a toggle-button (checkbox/radio)
        
        'locator' is an element locator
        """
        self.do_command("uncheck", [locator,])


    def select(self,selectLocator,optionLocator):
        """
        Select an option from a drop-down using an option locator.
        
        
        Option locators provide different ways of specifying options of an HTML
        Select element (e.g. for selecting a specific option, or for asserting
        that the selected option satisfies a specification). There are several
        forms of Select Option Locator.
        
        *    \ **label**\ =\ *labelPattern*
            matches options based on their labels, i.e. the visible text. (This
            is the default.)
            *    label=regexp:^[Oo]ther
            
            
        *    \ **value**\ =\ *valuePattern*
            matches options based on their values.
            *    value=other
            
            
        *    \ **id**\ =\ *id*
            matches options based on their ids.
            *    id=option1
            
            
        *    \ **index**\ =\ *index*
            matches an option based on its index (offset from zero).
            *    index=2
            
            
        
        
        If no option locator prefix is provided, the default behaviour is to match on \ **label**\ .
        
        
        
        'selectLocator' is an element locator identifying a drop-down menu
        'optionLocator' is an option locator (a label by default)
        """
        self.do_command("select", [selectLocator,optionLocator,])


    def add_selection(self,locator,optionLocator):
        """
        Add a selection to the set of selected options in a multi-select element using an option locator.
        
        @see #doSelect for details of option locators
        
        'locator' is an element locator identifying a multi-select box
        'optionLocator' is an option locator (a label by default)
        """
        self.do_command("addSelection", [locator,optionLocator,])


    def remove_selection(self,locator,optionLocator):
        """
        Remove a selection from the set of selected options in a multi-select element using an option locator.
        
        @see #doSelect for details of option locators
        
        'locator' is an element locator identifying a multi-select box
        'optionLocator' is an option locator (a label by default)
        """
        self.do_command("removeSelection", [locator,optionLocator,])


    def submit(self,formLocator):
        """
        Submit the specified form. This is particularly useful for forms without
        submit buttons, e.g. single-input "Search" forms.
        
        'formLocator' is an element locator for the form you want to submit
        """
        self.do_command("submit", [formLocator,])


    def open(self,url):
        """
        Opens an URL in the test frame. This accepts both relative and absolute
        URLs.
        
        The "open" command waits for the page to load before proceeding,
        ie. the "AndWait" suffix is implicit.
        
        \ *Note*: The URL must be on the same domain as the runner HTML
        due to security restrictions in the browser (Same Origin Policy). If you
        need to open an URL on another domain, use the Selenium Server to start a
        new browser session on that domain.
        
        'url' is the URL to open; may be relative or absolute
        """
        self.do_command("open", [url,])


    def open_window(self,url,windowID):
        """
        Opens a popup window (if a window with that ID isn't already open).
        After opening the window, you'll need to select it using the selectWindow
        command.
        
        This command can also be a useful workaround for bug SEL-339.  In some cases, Selenium will be unable to intercept a call to window.open (if the call occurs during or before the "onLoad" event, for example).
        In those cases, you can force Selenium to notice the open window's name by using the Selenium openWindow command, using
        an empty (blank) url, like this: openWindow("", "myFunnyWindow").
        
        
        'url' is the URL to open, which can be blank
        'windowID' is the JavaScript window ID of the window to select
        """
        self.do_command("openWindow", [url,windowID,])


    def select_window(self,windowID):
        """
        Selects a popup window; once a popup window has been selected, all
        commands go to that window. To select the main window again, use null
        as the target.
        
        Selenium has several strategies for finding the window object referred to by the "windowID" parameter.
        1.) if windowID is null, then it is assumed the user is referring to the original window instantiated by the browser).
        2.) if the value of the "windowID" parameter is a JavaScript variable name in the current application window, then it is assumed
        that this variable contains the return value from a call to the JavaScript window.open() method.
        3.) Otherwise, selenium looks in a hash it maintains that maps string names to window objects.  Each of these string 
        names matches the second parameter "windowName" past to the JavaScript method  window.open(url, windowName, windowFeatures, replaceFlag)
        (which selenium intercepts).
        If you're having trouble figuring out what is the name of a window that you want to manipulate, look at the selenium log messages
        which identify the names of windows created via window.open (and therefore intercepted by selenium).  You will see messages
        like the following for each window as it is opened:
        ``debug: window.open call intercepted; window ID (which you can use with selectWindow()) is "myNewWindow"``
        In some cases, Selenium will be unable to intercept a call to window.open (if the call occurs during or before the "onLoad" event, for example).
        (This is bug SEL-339.)  In those cases, you can force Selenium to notice the open window's name by using the Selenium openWindow command, using
        an empty (blank) url, like this: openWindow("", "myFunnyWindow").
        
        
        'windowID' is the JavaScript window ID of the window to select
        """
        self.do_command("selectWindow", [windowID,])


    def select_frame(self,locator):
        """
        Selects a frame within the current window.  (You may invoke this command
        multiple times to select nested frames.)  To select the parent frame, use
        "relative=parent" as a locator; to select the top frame, use "relative=top".
        
        You may also use a DOM expression to identify the frame you want directly,
        like this: ``dom=frames["main"].frames["subframe"]``
        
        
        'locator' is an element locator identifying a frame or iframe
        """
        self.do_command("selectFrame", [locator,])


    def get_log_messages(self):
        """
        Return the contents of the log.
        
        This is a placeholder intended to make the code generator make this API
        available to clients.  The selenium server will intercept this call, however,
        and return its recordkeeping of log messages since the last call to this API.
        Thus this code in JavaScript will never be called.
        The reason I opted for a servercentric solution is to be able to support
        multiple frames served from different domains, which would break a
        centralized JavaScript logging mechanism under some conditions.
        
        
        """
        return self.get_string("getLogMessages", [])


    def get_whether_this_frame_match_frame_expression(self,currentFrameString,target):
        """
        Determine whether current/locator identify the frame containing this running code.
        
        This is useful in proxy injection mode, where this code runs in every
        browser frame and window, and sometimes the selenium server needs to identify
        the "current" frame.  In this case, when the test calls selectFrame, this
        routine is called for each frame to figure out which one has been selected.
        The selected frame will return true, while all others will return false.
        
        
        'currentFrameString' is starting frame
        'target' is new frame (which might be relative to the current one)
        """
        return self.get_boolean("getWhetherThisFrameMatchFrameExpression", [currentFrameString,target,])


    def get_whether_this_window_match_window_expression(self,currentWindowString,target):
        """
        Determine whether currentWindowString plus target identify the window containing this running code.
        
        This is useful in proxy injection mode, where this code runs in every
        browser frame and window, and sometimes the selenium server needs to identify
        the "current" window.  In this case, when the test calls selectWindow, this
        routine is called for each window to figure out which one has been selected.
        The selected window will return true, while all others will return false.
        
        
        'currentWindowString' is starting window
        'target' is new window (which might be relative to the current one, e.g., "_parent")
        """
        return self.get_boolean("getWhetherThisWindowMatchWindowExpression", [currentWindowString,target,])


    def wait_for_pop_up(self,windowID,timeout):
        """
        Waits for a popup window to appear and load up.
        
        'windowID' is the JavaScript window ID of the window that will appear
        'timeout' is a timeout in milliseconds, after which the action will return with an error
        """
        self.do_command("waitForPopUp", [windowID,timeout,])


    def choose_cancel_on_next_confirmation(self):
        """
        By default, Selenium's overridden window.confirm() function will
        return true, as if the user had manually clicked OK.  After running
        this command, the next call to confirm() will return false, as if
        the user had clicked Cancel.
        
        """
        self.do_command("chooseCancelOnNextConfirmation", [])


    def answer_on_next_prompt(self,answer):
        """
        Instructs Selenium to return the specified answer string in response to
        the next JavaScript prompt [window.prompt()].
        
        'answer' is the answer to give in response to the prompt pop-up
        """
        self.do_command("answerOnNextPrompt", [answer,])


    def go_back(self):
        """
        Simulates the user clicking the "back" button on their browser.
        
        """
        self.do_command("goBack", [])


    def refresh(self):
        """
        Simulates the user clicking the "Refresh" button on their browser.
        
        """
        self.do_command("refresh", [])


    def close(self):
        """
        Simulates the user clicking the "close" button in the titlebar of a popup
        window or tab.
        
        """
        self.do_command("close", [])


    def is_alert_present(self):
        """
        Has an alert occurred?
        
        
        This function never throws an exception
        
        
        
        """
        return self.get_boolean("isAlertPresent", [])


    def is_prompt_present(self):
        """
        Has a prompt occurred?
        
        
        This function never throws an exception
        
        
        
        """
        return self.get_boolean("isPromptPresent", [])


    def is_confirmation_present(self):
        """
        Has confirm() been called?
        
        
        This function never throws an exception
        
        
        
        """
        return self.get_boolean("isConfirmationPresent", [])


    def get_alert(self):
        """
        Retrieves the message of a JavaScript alert generated during the previous action, or fail if there were no alerts.
        
        Getting an alert has the same effect as manually clicking OK. If an
        alert is generated but you do not get/verify it, the next Selenium action
        will fail.
        NOTE: under Selenium, JavaScript alerts will NOT pop up a visible alert
        dialog.
        NOTE: Selenium does NOT support JavaScript alerts that are generated in a
        page's onload() event handler. In this case a visible dialog WILL be
        generated and Selenium will hang until someone manually clicks OK.
        
        
        """
        return self.get_string("getAlert", [])


    def get_confirmation(self):
        """
        Retrieves the message of a JavaScript confirmation dialog generated during
        the previous action.
        
        
        By default, the confirm function will return true, having the same effect
        as manually clicking OK. This can be changed by prior execution of the
        chooseCancelOnNextConfirmation command. If an confirmation is generated
        but you do not get/verify it, the next Selenium action will fail.
        
        
        NOTE: under Selenium, JavaScript confirmations will NOT pop up a visible
        dialog.
        
        
        NOTE: Selenium does NOT support JavaScript confirmations that are
        generated in a page's onload() event handler. In this case a visible
        dialog WILL be generated and Selenium will hang until you manually click
        OK.
        
        
        
        """
        return self.get_string("getConfirmation", [])


    def get_prompt(self):
        """
        Retrieves the message of a JavaScript question prompt dialog generated during
        the previous action.
        
        Successful handling of the prompt requires prior execution of the
        answerOnNextPrompt command. If a prompt is generated but you
        do not get/verify it, the next Selenium action will fail.
        NOTE: under Selenium, JavaScript prompts will NOT pop up a visible
        dialog.
        NOTE: Selenium does NOT support JavaScript prompts that are generated in a
        page's onload() event handler. In this case a visible dialog WILL be
        generated and Selenium will hang until someone manually clicks OK.
        
        
        """
        return self.get_string("getPrompt", [])


    def get_location(self):
        """
        Gets the absolute URL of the current page.
        
        """
        return self.get_string("getLocation", [])


    def get_title(self):
        """
        Gets the title of the current page.
        
        """
        return self.get_string("getTitle", [])


    def get_body_text(self):
        """
        Gets the entire text of the page.
        
        """
        return self.get_string("getBodyText", [])


    def get_value(self,locator):
        """
        Gets the (whitespace-trimmed) value of an input field (or anything else with a value parameter).
        For checkbox/radio elements, the value will be "on" or "off" depending on
        whether the element is checked or not.
        
        'locator' is an element locator
        """
        return self.get_string("getValue", [locator,])


    def get_text(self,locator):
        """
        Gets the text of an element. This works for any element that contains
        text. This command uses either the textContent (Mozilla-like browsers) or
        the innerText (IE-like browsers) of the element, which is the rendered
        text shown to the user.
        
        'locator' is an element locator
        """
        return self.get_string("getText", [locator,])


    def get_eval(self,script):
        """
        Gets the result of evaluating the specified JavaScript snippet.  The snippet may
        have multiple lines, but only the result of the last line will be returned.
        
        Note that, by default, the snippet will run in the context of the "selenium"
        object itself, so ``this`` will refer to the Selenium object, and ``window`` will
        refer to the top-level runner test window, not the window of your application.
        If you need a reference to the window of your application, you can refer
        to ``this.browserbot.getCurrentWindow()`` and if you need to use
        a locator to refer to a single element in your application page, you can
        use ``this.page().findElement("foo")`` where "foo" is your locator.
        
        
        'script' is the JavaScript snippet to run
        """
        return self.get_string("getEval", [script,])


    def is_checked(self,locator):
        """
        Gets whether a toggle-button (checkbox/radio) is checked.  Fails if the specified element doesn't exist or isn't a toggle-button.
        
        'locator' is an element locator pointing to a checkbox or radio button
        """
        return self.get_boolean("isChecked", [locator,])


    def get_table(self,tableCellAddress):
        """
        Gets the text from a cell of a table. The cellAddress syntax
        tableLocator.row.column, where row and column start at 0.
        
        'tableCellAddress' is a cell address, e.g. "foo.1.4"
        """
        return self.get_string("getTable", [tableCellAddress,])


    def get_selected_labels(self,selectLocator):
        """
        Gets all option labels (visible text) for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedLabels", [selectLocator,])


    def get_selected_label(self,selectLocator):
        """
        Gets option label (visible text) for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedLabel", [selectLocator,])


    def get_selected_values(self,selectLocator):
        """
        Gets all option values (value attributes) for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedValues", [selectLocator,])


    def get_selected_value(self,selectLocator):
        """
        Gets option value (value attribute) for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedValue", [selectLocator,])


    def get_selected_indexes(self,selectLocator):
        """
        Gets all option indexes (option number, starting at 0) for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedIndexes", [selectLocator,])


    def get_selected_index(self,selectLocator):
        """
        Gets option index (option number, starting at 0) for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedIndex", [selectLocator,])


    def get_selected_ids(self,selectLocator):
        """
        Gets all option element IDs for selected options in the specified select or multi-select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectedIds", [selectLocator,])


    def get_selected_id(self,selectLocator):
        """
        Gets option element ID for selected option in the specified select element.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string("getSelectedId", [selectLocator,])


    def is_something_selected(self,selectLocator):
        """
        Determines whether some option in a drop-down menu is selected.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_boolean("isSomethingSelected", [selectLocator,])


    def get_select_options(self,selectLocator):
        """
        Gets all option labels in the specified select drop-down.
        
        'selectLocator' is an element locator identifying a drop-down menu
        """
        return self.get_string_array("getSelectOptions", [selectLocator,])


    def get_attribute(self,attributeLocator):
        """
        Gets the value of an element attribute.
        
        'attributeLocator' is an element locator followed by an
        """
        return self.get_string("getAttribute", [attributeLocator,])


    def is_text_present(self,pattern):
        """
        Verifies that the specified text pattern appears somewhere on the rendered page shown to the user.
        
        'pattern' is a pattern to match with the text of the page
        """
        return self.get_boolean("isTextPresent", [pattern,])


    def is_element_present(self,locator):
        """
        Verifies that the specified element is somewhere on the page.
        
        'locator' is an element locator
        """
        return self.get_boolean("isElementPresent", [locator,])


    def is_visible(self,locator):
        """
        Determines if the specified element is visible. An
        element can be rendered invisible by setting the CSS "visibility"
        property to "hidden", or the "display" property to "none", either for the
        element itself or one if its ancestors.  This method will fail if
        the element is not present.
        
        'locator' is an element locator
        """
        return self.get_boolean("isVisible", [locator,])


    def is_editable(self,locator):
        """
        Determines whether the specified input element is editable, ie hasn't been disabled.
        This method will fail if the specified element isn't an input element.
        
        'locator' is an element locator
        """
        return self.get_boolean("isEditable", [locator,])


    def get_all_buttons(self):
        """
        Returns the IDs of all buttons on the page.
        
        If a given button has no ID, it will appear as "" in this array.
        
        
        """
        return self.get_string_array("getAllButtons", [])


    def get_all_links(self):
        """
        Returns the IDs of all links on the page.
        
        If a given link has no ID, it will appear as "" in this array.
        
        
        """
        return self.get_string_array("getAllLinks", [])


    def get_all_fields(self):
        """
        Returns the IDs of all input fields on the page.
        
        If a given field has no ID, it will appear as "" in this array.
        
        
        """
        return self.get_string_array("getAllFields", [])


    def get_attribute_from_all_windows(self,attributeName):
        """
        Returns every instance of some attribute from all known windows.
        
        'attributeName' is name of an attribute on the windows
        """
        return self.get_string_array("getAttributeFromAllWindows", [attributeName,])


    def dragdrop(self,locator,movementsString):
        """
        deprecated - use dragAndDrop instead
        
        'locator' is an element locator
        'movementsString' is offset in pixels from the current location to which the element should be moved, e.g., "+70,-300"
        """
        self.do_command("dragdrop", [locator,movementsString,])


    def drag_and_drop(self,locator,movementsString):
        """
        Drags an element a certain distance and then drops it
        
        'locator' is an element locator
        'movementsString' is offset in pixels from the current location to which the element should be moved, e.g., "+70,-300"
        """
        self.do_command("dragAndDrop", [locator,movementsString,])


    def drag_and_drop_to_object(self,locatorOfObjectToBeDragged,locatorOfDragDestinationObject):
        """
        Drags an element and drops it on another element
        
        'locatorOfObjectToBeDragged' is an element to be dragged
        'locatorOfDragDestinationObject' is an element whose location (i.e., whose top left corner) will be the point where locatorOfObjectToBeDragged  is dropped
        """
        self.do_command("dragAndDropToObject", [locatorOfObjectToBeDragged,locatorOfDragDestinationObject,])


    def window_focus(self,windowName):
        """
        Gives focus to a window
        
        'windowName' is name of the window to be given focus
        """
        self.do_command("windowFocus", [windowName,])


    def window_maximize(self,windowName):
        """
        Resize window to take up the entire screen
        
        'windowName' is name of the window to be enlarged
        """
        self.do_command("windowMaximize", [windowName,])


    def get_all_window_ids(self):
        """
        Returns the IDs of all windows that the browser knows about.
        
        """
        return self.get_string_array("getAllWindowIds", [])


    def get_all_window_names(self):
        """
        Returns the names of all windows that the browser knows about.
        
        """
        return self.get_string_array("getAllWindowNames", [])


    def get_all_window_titles(self):
        """
        Returns the titles of all windows that the browser knows about.
        
        """
        return self.get_string_array("getAllWindowTitles", [])


    def get_html_source(self):
        """
        Returns the entire HTML source between the opening and
        closing "html" tags.
        
        """
        return self.get_string("getHtmlSource", [])


    def set_cursor_position(self,locator,position):
        """
        Moves the text cursor to the specified position in the given input element or textarea.
        This method will fail if the specified element isn't an input element or textarea.
        
        'locator' is an element locator pointing to an input element or textarea
        'position' is the numerical position of the cursor in the field; position should be 0 to move the position to the beginning of the field.  You can also set the cursor to -1 to move it to the end of the field.
        """
        self.do_command("setCursorPosition", [locator,position,])


    def get_element_index(self,locator):
        """
        Get the relative index of an element to its parent (starting from 0). The comment node and empty text node
        will be ignored.
        
        'locator' is an element locator pointing to an element
        """
        return self.get_number("getElementIndex", [locator,])


    def is_ordered(self,locator1,locator2):
        """
        Check if these two elements have same parent and are ordered. Two same elements will
        not be considered ordered.
        
        'locator1' is an element locator pointing to the first element
        'locator2' is an element locator pointing to the second element
        """
        return self.get_boolean("isOrdered", [locator1,locator2,])


    def get_element_position_left(self,locator):
        """
        Retrieves the horizontal position of an element
        
        'locator' is an element locator pointing to an element OR an element itself
        """
        return self.get_number("getElementPositionLeft", [locator,])


    def get_element_position_top(self,locator):
        """
        Retrieves the vertical position of an element
        
        'locator' is an element locator pointing to an element OR an element itself
        """
        return self.get_number("getElementPositionTop", [locator,])


    def get_element_width(self,locator):
        """
        Retrieves the width of an element
        
        'locator' is an element locator pointing to an element
        """
        return self.get_number("getElementWidth", [locator,])


    def get_element_height(self,locator):
        """
        Retrieves the height of an element
        
        'locator' is an element locator pointing to an element
        """
        return self.get_number("getElementHeight", [locator,])


    def get_cursor_position(self,locator):
        """
        Retrieves the text cursor position in the given input element or textarea; beware, this may not work perfectly on all browsers.
        
        Specifically, if the cursor/selection has been cleared by JavaScript, this command will tend to
        return the position of the last location of the cursor, even though the cursor is now gone from the page.  This is filed as SEL-243.
        
        This method will fail if the specified element isn't an input element or textarea, or there is no cursor in the element.
        
        'locator' is an element locator pointing to an input element or textarea
        """
        return self.get_number("getCursorPosition", [locator,])


    def set_context(self,context,logLevelThreshold):
        """
        Writes a message to the status bar and adds a note to the browser-side
        log.
        
        If logLevelThreshold is specified, set the threshold for logging
        to that level (debug, info, warn, error).
        (Note that the browser-side logs will \ *not* be sent back to the
        server, and are invisible to the Client Driver.)
        
        
        'context' is the message to be sent to the browser
        'logLevelThreshold' is one of "debug", "info", "warn", "error", sets the threshold for browser-side logging
        """
        self.do_command("setContext", [context,logLevelThreshold,])


    def get_expression(self,expression):
        """
        Returns the specified expression.
        
        This is useful because of JavaScript preprocessing.
        It is used to generate commands like assertExpression and waitForExpression.
        
        
        'expression' is the value to return
        """
        return self.get_string("getExpression", [expression,])


    def wait_for_condition(self,script,timeout):
        """
        Runs the specified JavaScript snippet repeatedly until it evaluates to "true".
        The snippet may have multiple lines, but only the result of the last line
        will be considered.
        
        Note that, by default, the snippet will be run in the runner's test window, not in the window
        of your application.  To get the window of your application, you can use
        the JavaScript snippet ``selenium.browserbot.getCurrentWindow()``, and then
        run your JavaScript in there
        
        
        'script' is the JavaScript snippet to run
        'timeout' is a timeout in milliseconds, after which this command will return with an error
        """
        self.do_command("waitForCondition", [script,timeout,])


    def set_timeout(self,timeout):
        """
        Specifies the amount of time that Selenium will wait for actions to complete.
        
        Actions that require waiting include "open" and the "waitFor*" actions.
        
        The default timeout is 30 seconds.
        
        'timeout' is a timeout in milliseconds, after which the action will return with an error
        """
        self.do_command("setTimeout", [timeout,])


    def wait_for_page_to_load(self,timeout):
        """
        Waits for a new page to load.
        
        You can use this command instead of the "AndWait" suffixes, "clickAndWait", "selectAndWait", "typeAndWait" etc.
        (which are only available in the JS API).
        Selenium constantly keeps track of new pages loading, and sets a "newPageLoaded"
        flag when it first notices a page load.  Running any other Selenium command after
        turns the flag to false.  Hence, if you want to wait for a page to load, you must
        wait immediately after a Selenium command that caused a page-load.
        
        
        'timeout' is a timeout in milliseconds, after which this command will return with an error
        """
        self.do_command("waitForPageToLoad", [timeout,])


    def get_cookie(self):
        """
        Return all cookies of the current page under test.
        
        """
        return self.get_string("getCookie", [])


    def create_cookie(self,nameValuePair,optionsString):
        """
        Create a new cookie whose path and domain are same with those of current page
        under test, unless you specified a path for this cookie explicitly.
        
        'nameValuePair' is name and value of the cookie in a format "name=value"
        'optionsString' is options for the cookie. Currently supported options include 'path' and 'max_age'.      the optionsString's format is "path=/path/, max_age=60". The order of options are irrelevant, the unit      of the value of 'max_age' is second.
        """
        self.do_command("createCookie", [nameValuePair,optionsString,])


    def delete_cookie(self,name,path):
        """
        Delete a named cookie with specified path.
        
        'name' is the name of the cookie to be deleted
        'path' is the path property of the cookie to be deleted
        """
        self.do_command("deleteCookie", [name,path,])

