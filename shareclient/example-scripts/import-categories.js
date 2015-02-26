/*
Example of import of categories using javascript (EX in javascript console)

It will create categories with the same name, do this before you import your site.

Remember nodeRef of ctegories are changed on new installation/server.

Author: Rasmus Melgaard, Novem-IT
Email: rm@novem-it.dk
*/

var catNtags = {
    "categories": [], 
    "tags": []
};
/* add result of export-categories.py

var catNtags = {
    "categories": [
        {
            "children": [
                {
....
		}
                    
        }
    ], 
    "tags": [
        ....
    ]
}; */

function category(cat) {
	logger.log("cat: " + cat.name);
	if (cat.children) {
		categories(cat.children);
	}
}

function categories(cats) {
  for (var i = 0, len=cats.length; i<len;i++) {
	category(cats[i]);
  }
}

function tag(t) {
	logger.log("tag: " + t);
	if (t.children) {
		tags(t.children);
	}
}

function tags(tags) {
  for (var i = 0, len=tags.length; i<len;i++) {
	tag(tags[i]);
  }
}

function createCategory(nodeParent, cat) {
	logger.log("NodeParent: " + nodeParent.name + "cat: " + cat.name);
        var props = new Array();
        props["cm:name"] = cat.name;
	props["cm:description"] = cat.description;
	//props["cm:hasChildren"] = cat.hasChildren;
	props["cm:nodeRef"] = cat.nodeRef;
	//workspace://SpacesStore
	//cm:categoryRoot && type:  cm:category_root
	//cm:generalclassifiable || cm:taggable aspect ... type:  cm:category assoc: cm:categories
	//cm:subcategories assoc
	var newNode = null;
	var nodeExists = false;
        for each(node in nodeParent.childAssocs["cm:subcategories"]) {
	    logger.log("checking child: " + node.name);
		if (node.name == cat.name) { 	            	
			newNode = node;
			nodeExists = true;
			logger.log("found: " + cat.name);
			break;
		
		}
	
	}
	if (!nodeExists) {
		logger.log("creating new: " + cat.name);
		newNode = nodeParent.createNode(cat.name, "{http://www.alfresco.org/model/content/1.0}category", props, "cm:subcategories"); //alt: nodeParent.createSubCategory(cat.name)
	}
	if (null != newNode && cat.hasChildren) {
		var cats=cat.children;
		for (var i = 0, len=cats.length; i<len;i++) {
			createCategory(newNode, cats[i]);
	 	}
	}
}
for each (root in classification.getRootCategories("cm:generalclassifiable")) logger.log("root:: " + root.name);

var realRoot = classification.getRootCategories("cm:generalclassifiable")[0].parent;

for (var i = 0, len=catNtags.categories.length; i<len;i++) {
	logger.log("rootCategory:: " + catNtags.categories[i].name);
	createCategory(realRoot, catNtags.categories[i]);
}


//categories(catNtags.categories);
//tags(catNtags.tags);
