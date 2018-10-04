#!/usr/bin/env python

import sys, random
from os import path
from xml.dom.minidom import Document, Element, Attr

X3DOM_CSS = "./x3dom-v1.0.css"
X3DOM_JS = "./x3dom-v1.0.js"

CUSTOM_JS = "./aer2x3dom.js"

X3D_NS = "http://www.web3d.org/specifications/x3d-namespace"
XHTML_NS = "http://www.w3.org/1999/xhtml"

ANCHOR_TEXTURE_ADDED = False

CONNECTORS = {}

def dom_for_aer_array(aer_array, item_type=str):
	aer_array = aer_array.split(",")
	assert int(aer_array[0]) == len(aer_array) - 1
	aer_array[1:] = [str(item_type(item)) for item in aer_array[1:]]
	return aer_array[1:]

def dom_str_for_aer_array(aer_array, item_type=None):
	return " ".join(dom_for_aer_array(aer_array, item_type))

def abs_url(base_url, rel_url):
	return base_url + "/" + rel_url if base_url else rel_url

def dom_for_aer_line(doc, aer_line):
	global CONNECTORS
	
	root = doc.getElementsByTagName("x3d")[0]
	orig_url = root.getAttribute("altSrc")
	if orig_url:
		orig_url = path.split(orig_url)[0] + "/"
	
	aer_line = aer_line.split(":")
	aer_type = aer_line[0][:4]
	aer_id = aer_line[0][4:]
	
	# Parse the line.
	aer_data = {}
	for pair in aer_line[1:]:
		pair = pair.split("=", 1)
		aer_data[pair[0]] = pair[1] if len(pair) > 1 else None
	
	# Special element types.
	if aer_type == "HEAD":
		if aer_data.get("DFmt") != "A":
			print >> sys.stderr, "Binary Atmosphere model files not supported."
			sys.exit(1)
		return None
	elif aer_type == "NEN3" and aer_data.get("name") == "Viewer":
		root.setAttribute("altImg", aer_data["icon"])
		return None
	elif aer_type == "WRLD":
		root.setAttribute("id", aer_data.get("wlnm"))
		root.setAttribute("title", aer_data.get("irtc"))
		url = aer_data.get("iref")
		if url:
			root.setAttribute("altSrc", url.replace("|", ":"))
		return None
	
	# Resource element types.
	if aer_type == "ACTR":
		viewport = doc.createElement("viewport")
		# TODO: viewport.position
#		viewport.setAttribute("position",
#							  dom_str_for_aer_array(aer_data.get("lkdr"), float))
#		viewport.setAttribute("orientation",
#							  dom_str_for_aer_array(aer_data.get("oRnt"), float))
		return viewport
	elif aer_type == "CON3":
		if "vals" in aer_data and aer_id not in CONNECTORS:
			CONNECTORS[aer_id] = tuple(dom_for_aer_array(aer_data["vals"],
														 float))
		return None
	elif aer_type == "STCL":
		appearance = doc.createElement("appearance")
		appearance.setAttribute("def", "%s%s" % (aer_type, aer_id))
		material = doc.createElement("material")
		material.appendChild(doc.createTextNode(""))
		r = float(aer_data.get("sred", 0))
		g = float(aer_data.get("sgrn", 0))
		b = float(aer_data.get("sblu", 0))
		material.setAttribute("diffuseColor", "%f %f %f" % (r, g, b))
		appearance.appendChild(material)
		return appearance
	elif aer_type == "TXTR":
		appearance = doc.createElement("appearance")
		appearance.setAttribute("def", "%s%s" % (aer_type, aer_id))
		material = doc.createElement("imagetexture")
		material.appendChild(doc.createTextNode(""))
		material.setAttribute("url", abs_url(orig_url, aer_data.get("urln")))
		appearance.appendChild(material)
		return appearance
	
	transform = doc.createElement("transform")
	transform.setAttribute("translation", "0 0 0")								# debug
	
	# Set common attributes.
	shape = doc.createElement("shape")
#	shape.setAttribute("DEF", "%s%s" % (aer_type, aer_id))
	start_pt = None
	if "obnm" in aer_data:
		shape.setAttribute("id", aer_data["obnm"])
	if "cn3s" in aer_data:
		connector_idxs = dom_for_aer_array(aer_data["cn3s"])
		connectors = [CONNECTORS[idx] for idx in connector_idxs
					  if idx in CONNECTORS]
		if len(connectors):
			start_pt = [float(i) for i in connectors[0]]
			transform.setAttribute("translation", "%f %f %f" % tuple(start_pt))
	transform.appendChild(shape)
	appearance_id = None
	
	# Determine the model element type.
	if aer_type == "BOX3":
		box = doc.createElement("box")
		box.appendChild(doc.createTextNode(""))
		box.setAttribute("solid", "true")
		shape.appendChild(box)
		if len(connectors) > 1:
			end_pt = [float(i) for i in connectors[1]]
			scale = [(e - s) / 2 for s, e in zip(start_pt, end_pt)]
			transform.setAttribute("scale", "%f %f %f" % tuple(scale))
	elif aer_type == "COL3":
		cylinder = doc.createElement("cylinder")
		cylinder.appendChild(doc.createTextNode(""))
		cylinder.setAttribute("radius", str(float(aer_data.get("widt"))))
		shape.appendChild(cylinder)
		cylinder.setAttribute("solid", "false")
		if len(connectors) > 1:
			end_pt = [float(i) for i in connectors[1]]
			# TODO: transform.rotation for cylinders
			height = end_pt[1] - start_pt[1]
			transform.setAttribute("scale", "0 %f 0" % height)
	elif aer_type == "FLR3":
		box = doc.createElement("box")
		box.appendChild(doc.createTextNode(""))
		box.setAttribute("solid", "true")
		transform.setAttribute("scale", "1 1 %f" % float(aer_data.get("thik", 1)))		# debug
		shape.appendChild(box)
		start_pt[2] += float(aer_data.get("plny", 0))
		transform.setAttribute("translation", "0 %f 0" % tuple(start_pt))
	elif aer_type == "PORT":
		anchor = doc.createElement("anchor")
		anchor.setAttribute("url", abs_url(orig_url, aer_data.get("wrul")))
		transform.appendChild(anchor)
		
		sphere = doc.createElement("sphere")
		sphere.appendChild(doc.createTextNode(""))
		sphere.setAttribute("solid", "true")
		shape.appendChild(sphere)
		
		transform.removeChild(shape)
		anchor.appendChild(shape)
		
		start_pt = start_pt or [0, 1.5, 0]										# debug
		transform.setAttribute("translation", "%f %f %f" % tuple(start_pt))
		
		global ANCHOR_TEXTURE_ADDED
		appearance_id = "_anchor_texture"
		if not ANCHOR_TEXTURE_ADDED:
			appearance = doc.createElement("appearance")
			appearance.setAttribute("id", "_anchor_texture")
			appearance.setAttribute("def", "_anchor_texture")
			material = doc.createElement("material")
			material.appendChild(doc.createTextNode(""))
			material.setAttribute("emissiveColor", "0 0 1")
			material.setAttribute("transparency", "0.4")
			appearance.appendChild(material)
			
			collision = doc.getElementsByTagName("collision")[0]
			collision.appendChild(appearance)
			ANCHOR_TEXTURE_ADDED = True
	else:
		return doc.createComment("Unsupported element type %s" % aer_type)
	
	# TODO: shape.appearance
	if len(doc.getElementsByTagName("appearance")):
		appearance = doc.createElement("appearance")
		appearance.appendChild(doc.createTextNode(""))
		if not appearance_id:
			appearance_idx = random.randint(0, len(doc.getElementsByTagName("appearance")) - 1)	# debug
			appearance_id = doc.getElementsByTagName("appearance")[appearance_idx].getAttribute("def")
		appearance.setAttribute("use", appearance_id)
		shape.appendChild(appearance)
	
#	return shape
	return transform

def html_with_model(x3d_doc):
	x3d_root = x3d_doc.getElementsByTagName("x3d")[0]
	
	doc = Document()
	
	root = doc.createElement("html")
	root.namespaceURI = XHTML_NS
	root.setAttribute("xmlns", root.namespaceURI)
	
	doc.appendChild(root)
	orig_url = x3d_root.getAttribute("altSrc")
	if orig_url:
		root.setAttributeNS("xml", "xml:base", path.split(orig_url)[0] + "/")
	head = doc.createElement("head")
	root.appendChild(head)
	
	title = doc.createElement("title")
	model_title = x3d_root.getAttribute("title")
	title.appendChild(doc.createTextNode(model_title))
	head.appendChild(title)
	
	meta_generator = doc.createElement("meta")
	meta_generator.setAttribute("name", "generator")
	meta_generator.setAttribute("content", "aer2x3dom")
	head.appendChild(meta_generator)
	
	link_icon = doc.createElement("link")
	link_icon.setAttribute("rel", "icon")
	link_icon.setAttribute("href", x3d_root.getAttribute("altImg"))
	link_icon.setAttribute("type", "image/png")
	head.appendChild(link_icon)
	
	link_css = doc.createElement("link")
	link_css.setAttribute("rel", "stylesheet")
	link_css.setAttribute("type", "text/css")
	link_css.setAttribute("media", "screen")
	link_css.setAttribute("href", X3DOM_CSS)
	head.appendChild(link_css)
	
	script = doc.createElement("script")
	script.setAttribute("type", "text/javascript")
	script.setAttribute("src", CUSTOM_JS)
	script.appendChild(doc.createTextNode(""))
	head.appendChild(script)
	
	body = doc.createElement("body")
	root.appendChild(body)
	
	h1 = doc.createElement("h1")
	h1.appendChild(doc.createTextNode(model_title))
	body.appendChild(h1)
	
	x3d_root.setAttribute("width", "600px")
	x3d_root.setAttribute("height", "400px")
	body.appendChild(x3d_root)
	
	p_source = doc.createElement("p")
	p_source.appendChild(doc.createTextNode("Source:"))
	a_source = doc.createElement("a")
	a_source.setAttribute("href", orig_url)
	a_source.appendChild(doc.createTextNode("Adobe Atmosphere format"))
	p_source.appendChild(a_source)
	body.appendChild(p_source)
	
	script = doc.createElement("script")
	script.setAttribute("type", "text/javascript")
	script.setAttribute("src", X3DOM_JS)
	script.appendChild(doc.createTextNode(""))
	body.appendChild(script)
	
	return doc

def main():
	aer_path = None
	html = False
	for arg in sys.argv[1:]:
		if arg in ["--html", "-xhtml"]:
			html = True
		else:
			aer_path = arg
	if not aer_path:
		print >> sys.stderr, "No Atmosphere model file specified."
		sys.exit(1)
	
	doc = Document()
	
	root = doc.createElement("x3d")
	root.namespaceURI = X3D_NS
	root.setAttribute("xmlns", root.namespaceURI)
	doc.appendChild(root)
	
	scene = doc.createElement("scene")
	root.appendChild(scene)
	
	collision = doc.createElement("collision")
	scene.appendChild(collision)
	
	background = doc.createElement("background")
	background.appendChild(doc.createTextNode(""))
	background.setAttribute("groundColor", "0.2 0.2 0.2")
	background.setAttribute("skyColor", "0.8 0.8 0.98")
	collision.appendChild(background)
	
	with open(aer_path, "r") as aer_file:
		for aer_line in aer_file:
			elt = dom_for_aer_line(doc, aer_line)
			if not elt:
				continue
			collision.appendChild(elt)
	
	xml_path = path.splitext(aer_path)[0]
	xml_path += ".html" if html else ".x3d"
	with open(xml_path, "w") as xml_file:
		if not html:
			print >> xml_file, doc.toprettyxml()
			return
		
		html_doc = html_with_model(doc)
		if html_doc:
			print >> xml_file, html_doc.toprettyxml()

if __name__ == "__main__":
	main()
