function anchorOnMouseOver(evt) {
	var div = document.getElementsByClassName("x3dom-canvasdiv")[0];
	div.style.cursor = "pointer";
	alert("in");
}

function anchorOnMouseOut(evt) {
	var div = document.getElementsByClassName("x3dom-canvasdiv")[0];
	div.style.cursor = "move";
	alert("out");
}

function attachAnchorOnClick(evt) {
	var x3d = document.getElementsByTagName("x3d")[0];
	var anchors = x3d.getElementsByTagName("anchor");
	for (var anchor in anchors) {
		anchor.addEventListener("mouseover", anchorOnMouseOver, false);
		anchor.addEventListener("mouseout", anchorOnMouseOut, false);
	}
}

document.addEventListener("load", attachAnchorOnClick, false);
