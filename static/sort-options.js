function compareOptionText(a, b) {
	// case-insensitive comparison
	var aa = a.text.toLowerCase();
	var bb = b.text.toLowerCase();
	return aa!=bb ? (aa<bb ? -1 : 1) : 0;
}


function sortOptions(list) {
	// the first item in the list must not be moved
	var items = list.options.length - 1;
	if (items<=0) return;

	// create array and make copies of options in list
	var tmpArray = new Array(items);
	for (var i=0; i<items; i++) {
		var opt = list.options[i+1];
		tmpArray[i] = { text: opt.text, value: opt.value, defaultSelected: opt.defaultSelected }
	}

	// sort options
	tmpArray.sort(compareOptionText);

	// fetch the sorted options back to the original list
	for (var i=0; i<items; i++) {
		list.options[i+1].text = tmpArray[i].text;
		list.options[i+1].value = tmpArray[i].value;
		list.options[i+1].selected = tmpArray[i].defaultSelected;
	}
}


function sortOptionsInit() {
	var options = css.getElementsByClass(document, 'sort-onload', 'select')
	for (var i = options.length-1; i >= 0; i--) sortOptions(options[i]);
}


addEvent(window, 'load', sortOptionsInit)
