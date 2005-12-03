/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.HtmlDatePicker");
dojo.require("dojo.widget.HtmlWidget");
dojo.require("dojo.widget.DatePicker");

/*
	Some assumptions:
	- I'm planning on always showing 42 days at a time, and we can scroll by week,
	not just by month or year
	- To get a sense of what month to highlight, I basically initialize on the 
	first Saturday of each month, since that will be either the first of two or 
	the second of three months being partially displayed, and then I work forwards 
	and backwards from that point.
	Currently, I assume that dates are stored in the RFC 3339 format,
	because I find it to be most human readable and easy to parse
	http://www.faqs.org/rfcs/rfc3339.html: 		2005-06-30T08:05:00-07:00
	FIXME: scroll by week not yet implemented
*/


dojo.widget.HtmlDatePicker = function(){
	dojo.widget.DatePicker.call(this);
	dojo.widget.HtmlWidget.call(this);

	var _this = this;
	// today's date, JS Date object
	this.today = "";
	// selected date, JS Date object
	this.date = "";
	// rfc 3339 date
	this.storedDate = "";
	// date currently selected in the UI, stored in year, month, date in the format that will be actually displayed
	this.currentDate = {};
	// stored in year, month, date in the format that will be actually displayed
	this.firstSaturday = {};
	this.classNames = {
		previous: "previousMonth",
		current: "currentMonth",
		next: "nextMonth",
		currentDate: "currentDate",
		selectedDate: "selectedItem"
	}

	this.templateCssPath = dojo.uri.dojoUri("src/widget/templates/HtmlDatePicker.css");
	
	this.fillInTemplate = function(){
		this.initData();
		this.initUI();
	}
	
	this.initData = function() {
		this.today = new Date();
		if(this.storedDate) {
			this.date = fromRfcDate();
		} else {
			this.date = this.today;
		}
		// calendar math is simplified if time is set to 0
		this.today.setHours(0);
		this.date.setHours(0);
		this.initFirstSaturday(this.date.getMonth(), this.date.getFullYear());
	}
	
	this.setDate = function() {
		this.today = new Date();
		return this.toRfcDate(this.today);
	}
	
	this.toRfcDate =function(jsDate) {
		dj_unimplemented("dojo.widget.HtmlDatePicker.toRfcDate");
		//return rfcDate;
	}
	
	this.fromRfcDate = function(rfcDate) {
		var tempDate = rfcDate.split("-");
		// fullYear, month, date
		return new Date(parseInt(tempDate[0]), (parseInt(tempDate[1], 10) - 1), parseInt(tempDate[2].substr(0,2), 10));
	}
	
	this.initFirstSaturday = function(month, year) {
		if(!month) {
			month = this.date.getMonth();
		}
		if(!year) {
			year = this.date.getFullYear();
		}
		var firstOfMonth = new Date(year, month, 1);
		this.firstSaturday.year = year;
		this.firstSaturday.month = month;
		this.firstSaturday.date = 7 - firstOfMonth.getDay();
	}
	
	this.initUI = function() {
		var currentClassName = "";
		var previousDate = new Date();
		var calendarNodes = this.calendarDatesContainerNode.getElementsByTagName("td");
		var currentCalendarNode;
		previousDate.setHours(0);
		var nextDate = new Date(this.firstSaturday.year, this.firstSaturday.month, this.firstSaturday.date, 0);

		
		if(this.firstSaturday.date < 7) {
			// this means there are days to show from the previous month
			var dayInWeek = 6;
			for (var i=this.firstSaturday.date; i>0; i--) {
				currentCalendarNode = calendarNodes.item(dayInWeek);
				currentCalendarNode.innerHTML = nextDate.getDate();
				dojo.xml.htmlUtil.setClass(currentCalendarNode, this.getDateClassName(nextDate, "current"));
				dayInWeek--;
				previousDate = nextDate;
				nextDate = this.incrementDate(nextDate, false);
			}
			for(var i=dayInWeek; i>-1; i--) {
				currentCalendarNode = calendarNodes.item(i);
				currentCalendarNode.innerHTML = nextDate.getDate();
				dojo.xml.htmlUtil.setClass(currentCalendarNode, this.getDateClassName(nextDate, "previous"));
				previousDate = nextDate;
				nextDate = this.incrementDate(nextDate, false);				
			}
		} else {
			nextDate.setDate(0);
			for(var i=0; i<7; i++) {
				currentCalendarNode = calendarNodes.item(i);
				currentCalendarNode.innerHTML = i + 1;
				dojo.xml.htmlUtil.setClass(currentCalendarNode, this.getDateClassName(nextDate, "current"));
				previousDate = nextDate;
				nextDate = this.incrementDate(nextDate, true);				
			}
		}
		previousDate.setDate(this.firstSaturday.date);
		previousDate.setMonth(this.firstSaturday.month);
		previousDate.setFullYear(this.firstSaturday.year);
		nextDate = this.incrementDate(previousDate, true);
		var count = 7;
		currentCalendarNode = calendarNodes.item(count);
		while((nextDate.getMonth() == previousDate.getMonth()) && (count<42)) {
			currentCalendarNode.innerHTML = nextDate.getDate();
			dojo.xml.htmlUtil.setClass(currentCalendarNode, this.getDateClassName(nextDate, "current"));
			currentCalendarNode = calendarNodes.item(++count);
			previousDate = nextDate;
			nextDate = this.incrementDate(nextDate, true);
		}
		
		while(count < 42) {
			currentCalendarNode.innerHTML = nextDate.getDate();
			dojo.xml.htmlUtil.setClass(currentCalendarNode, this.getDateClassName(nextDate, "next"));
			currentCalendarNode = calendarNodes.item(++count);
			previousDate = nextDate;
			nextDate = this.incrementDate(nextDate, true);
		}
		this.setMonthLabel(this.firstSaturday.month);
		this.setYearLabels(this.firstSaturday.year);
	}
	
	this.incrementDate = function(date, bool) {
		// bool: true to increase, false to decrease
		var time = date.getTime();
		var increment = 1000 * 60 * 60 * 24;
		time = (bool) ? (time + increment) : (time - increment);
		var returnDate = new Date();
		returnDate.setTime(time);
		return returnDate;
	}
	
	this.onIncrementWeek = function(evt) {
		evt.stopPropagation();
		switch(evt.target) {
			case this.increaseWeekNode:
				break;
			case this.decreaseWeekNode:
				break;
		}
	}

	this.onIncrementMonth = function(evt) {
		evt.stopPropagation();
		var month = this.firstSaturday.month;
		var year = this.firstSaturday.year;
		switch(evt.currentTarget) {
			case this.increaseMonthNode:
				if(month < 11) {
					month++;
				} else {
					month = 0;
					year++;
					
					this.setYearLabels(year);
				}
				break;
			case this.decreaseMonthNode:
				if(month > 0) {
					month--;
				} else {
					month = 11;
					year--;
					this.setYearLabels(year);
				}
				break;
			case this.increaseMonthNode.getElementsByTagName("img").item(0):
				if(month < 11) {
					month++;
				} else {
					month = 0;
					year++;
					this.setYearLabels(year);
				}
				break;
			case this.decreaseMonthNode.getElementsByTagName("img").item(0):
				if(month > 0) {
					month--;
				} else {
					month = 11;
					year--;
					this.setYearLabels(year);
				}
				break;
		}
		this.initFirstSaturday(month, year);
		this.initUI();
	}
	
	this.onIncrementYear = function(evt) {
		evt.stopPropagation();
		var year = this.firstSaturday.year;
		switch(evt.target) {
			case this.nextYearLabelNode:
				year++;
				break;
			case this.previousYearLabelNode:
				year--;
				break;
		}
		this.initFirstSaturday(this.firstSaturday.month, year);
		this.initUI();
	}

	this.setMonthLabel = function(monthIndex) {
		this.monthLabelNode.innerHTML = this.months[monthIndex];
	}
	
	this.setYearLabels = function(year) {
		this.previousYearLabelNode.innerHTML = year - 1;
		this.currentYearLabelNode.innerHTML = year;
		this.nextYearLabelNode.innerHTML = year + 1;
	}
	
	this.getDateClassName = function(date, monthState) {
		var currentClassName = this.classNames[monthState];
		if ((!this.selectedIsUsed) && (date.getDate() == this.date.getDate()) && (date.getMonth() == this.date.getMonth()) && (date.getFullYear() == this.date.getFullYear())) {
			currentClassName = this.classNames.selectedDate + " " + currentClassName;
			this.selectedIsUsed = 1;
		}
		if((!this.currentIsUsed) && (date.getDate() == this.today.getDate()) && (date.getMonth() == this.today.getMonth()) && (date.getFullYear() == this.today.getFullYear())) {
			currentClassName = currentClassName + " "  + this.classNames.currentDate;
			this.todayIsUsed = 1;
		}
		return currentClassName;
	}

	this.onClick = function(evt) {
		dojo.event.browser.stopEvent(evt)
	}
	
	this.onSetDate = function(evt) {
		dojo.event.browser.stopEvent(evt);
		this.selectedIsUsed = 0;
		this.todayIsUsed = 0;
		var month = this.firstSaturday.month;
		var year = this.firstSaturday.year;
		if (dojo.xml.htmlUtil.hasClass(evt.target, this.classNames["next"])) {
			month = ++month % 12;
			// if month is now == 0, add a year
			year = (month==0) ? ++year : year;
		} else if (dojo.xml.htmlUtil.hasClass(evt.target, this.classNames["previous"])) {
			month = --month % 12;
			// if month is now == 0, add a year
			year = (month==11) ? --year : year;
		}
		this.date = new Date(year, month, evt.target.innerHTML);
		this.initUI();
	}
	
	this.onChange = function(evt) {
		if(evt) {
			evt.preventDefault();
		}
		// add values to change the date and time
	}
	
	this.uninitialize = function() {

	}
	
	this.onDropdown = function(evt) {
		if(evt) {
			evt.preventDefault();
		}
		this.dateTimeSelectorNode.style.display = (this.dateTimeSelectorNode.style.display == "block") ? "none" : "block";
	}
	
	this.onCancel = function(evt) {
		if(evt.target != this.dateTimeDropdownImage && evt.target != this.dateTimeDropdown) {
			this.dateTimeSelectorNode.style.display = "none";
		}
	}
	
}
dj_inherits(dojo.widget.HtmlDatePicker, dojo.widget.HtmlWidget);

dojo.widget.HtmlDatePicker.prototype.templateString = '<div class="monthCalendarContainer" dojoAttachPoint="calendarContainerNode"><h3 class="monthLabel"><!--<span dojoAttachPoint="decreaseWeekNode" dojoAttachEvent="onClick: onIncrementWeek;" class="incrementControl"><img src="' + djConfig.baseRelativePath+ 'src/widget/templates/decrementWeek.gif" alt="&uarr;" /></span>--><span dojoAttachPoint="decreaseMonthNode" dojoAttachEvent="onClick: onIncrementMonth;" class="incrementControl"><img src="' + djConfig.baseRelativePath+ 'src/widget/templates/decrementMonth.gif" alt="&uarr;"></span><span dojoAttachPoint="monthLabelNode" class="month">July</span><span dojoAttachPoint="increaseMonthNode" dojoAttachEvent="onClick: onIncrementMonth;" class="incrementControl"><img src="' + djConfig.baseRelativePath+ 'src/widget/templates/incrementMonth.gif" alt="&darr;"></span><!--<span dojoAttachPoint="increaseWeekNode" dojoAttachEvent="onClick: onIncrementWeek;" class="incrementControl"><img src="' + djConfig.baseRelativePath+ 'src/widget/templates//incrementWeek.gif" alt="&darr;" /></span>--></h3><table class="calendarContainer"><thead> <tr><td>Su</td><td>Mo</td><td>Tu</td><td>We</td><td>Th</td><td>Fr</td><td>Sa</td></tr> </thead> <tbody dojoAttachPoint="calendarDatesContainerNode"  dojoAttachEvent="onClick: onSetDate;"> <tr dojoAttachPoint="calendarRow0"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr> <tr dojoAttachPoint="calendarRow1"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr> <tr dojoAttachPoint="calendarRow2"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr> <tr dojoAttachPoint="calendarRow3"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr> <tr dojoAttachPoint="calendarRow4"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr> <tr dojoAttachPoint="calendarRow5"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr> </tbody></table><h3 class="yearLabel"><span dojoAttachPoint="previousYearLabelNode" dojoAttachEvent="onClick: onIncrementYear;" class="previousYear"></span> <span class="selectedYear" dojoAttachPoint="currentYearLabelNode"></span> <span dojoAttachPoint="nextYearLabelNode" dojoAttachEvent="onClick: onIncrementYear;" class="nextYear"></span></h3></div>';
