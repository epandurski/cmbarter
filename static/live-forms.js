function highlightField() {
	css.addClassToElement(this, 'highlighted');
}


function resetFields() {
	for (var i = 0; i < this.elements.length; i++) {
		var elm = this.elements[i];
		if (elm.type == 'text') css.removeClassFromElement(elm, 'highlighted');
	}
	return true;
}


function liveFormsInit() {
	var forms = css.getElementsByClass(document, 'highlight-changed-fields', 'form')
	for (var i = 0; i < forms.length; i++) {
		var form = forms[i]
		for (var j = 0; j < form.elements.length; j++) {
			var elm = form.elements[j];
			if (elm.type == 'text') elm.onchange = highlightField;
		}
		addEvent(form, 'reset', resetFields);
	}
}


addEvent(window, 'load', liveFormsInit)
