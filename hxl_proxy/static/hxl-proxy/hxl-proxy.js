////////////////////////////////////////////////////////////////////////
// JavaScript library for the HXL Proxy
//
// All functions and varibles appear as properties of the hxl_proxy
// object.
////////////////////////////////////////////////////////////////////////


/**
 * Root object for all HXL Proxy functions and variables.
 */
var hxl_proxy = {};


/**
 * General configuration parameters
 */
hxl_proxy.config = {
    gdriveDeveloperKey: 'UNSPECIFIED',
    gdriveClientId: 'UNSPECIFIED'
};


////////////////////////////////////////////////////////////////////////
// File choosers for cloud services.
//
// Callbacks for choosing a file from an external service.
////////////////////////////////////////////////////////////////////////

hxl_proxy.choosers = {};


/**
 * Select a resource from the Humanitarian Data Exchange
 *
 * @param elementId the HTML id of the form input element where
 * the URL should appear.
 * @param submit if true, submit the form on success (default: false)
 * @returns always false.
 */
hxl_proxy.choosers.hdx = function(elementId, submit) {
    hdx.choose(function (resource) {
        var url = 'https://data.humdata.org/dataset/' + resource.package_id + '/resource/' + resource.id
        $(elementId).val(url);
        if (submit) {
            $(elementId).closest('form').submit();
        }
    });
    return false;
};


/**
 * Select a file from Dropbox.
 *
 * @param elementId the HTML id of the form input element where
 * the URL should appear.
 * @param submit if true, submit the form on success (default: false)
 * @returns always false.
 */
hxl_proxy.choosers.dropbox = function(elementId, submit) {
    Dropbox.choose({
        success: function(files) {
            $(elementId).val(files[0].link)
            if (submit) {
                $(elementId).closest('form').submit();
            }
        }
    });
    return false;
};


/**
 * Select a spreadsheet from Google Drive
 *
 * Relies on the hxl_proxy.config.gdriveDeveloperKey and the
 * hxl_proxy.config.gdriveClientId properties.
 *
 * Google makes this very difficult (compared to Dropbox).
 *
 * @param elementId the HTML id of the form input element where
 * the URL should appear.
 * @param submit if true, submit the form on success (default: false)
 * @returns always false.
 */
hxl_proxy.choosers.googleDrive = function(elementId, submit) {

    // We want to see only spreadsheets
    var scope = ['https://www.googleapis.com/auth/drive.readonly'];

    var pickerApiLoaded = false;
    var oauthToken = null;

    // Make a picker
    function createPicker() {
        if (pickerApiLoaded && oauthToken) {
            var view = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS);
            view.setMode(google.picker.DocsViewMode.LIST);
            var picker = new google.picker.PickerBuilder().
                addView(view).
                enableFeature(google.picker.Feature.NAV_HIDDEN).
                setOAuthToken(oauthToken).
                setDeveloperKey(hxl_proxy.config.gdriveDeveloperKey).
                setCallback(callback).
                build();
            picker.setVisible(true);
            // kludge to make sure it's in front of any modals
            $('.picker-dialog').css('z-index', '3000');
        }
    }

    // Handle the authorisation, if needed
    function onAuthApiLoad() {
        window.gapi.auth.authorize(
            {
                'client_id': hxl_proxy.config.gdriveClientId,
                'scope': scope,
                'immediate': false
            },
            function(authResult) {
                if (authResult && !authResult.error) {
                    oauthToken = authResult.access_token;
                    createPicker();
                }
            }
        );
    }

    // On success, create the picker.
    function onPickerApiLoad() {
        pickerApiLoaded = true;
        createPicker();
    }

    // Put the URL in the specified element
    function callback(data) {
        var url, doc;
        if (data[google.picker.Response.ACTION] == google.picker.Action.PICKED) {
            doc = data[google.picker.Response.DOCUMENTS][0];
            if (doc) {
                $(elementId).val(doc[google.picker.Document.URL]);
                if (submit) {
                    $(elementId).closest('form').submit();
                }
            }
        }
    }

    // Execute the commands.
    gapi.load('auth', {'callback': onAuthApiLoad});
    gapi.load('picker', {'callback': onPickerApiLoad});
    return false;
};


////////////////////////////////////////////////////////////////////////
// User-interface functions.
//
// Functions for manipulating the DOM or responding to user actions.
////////////////////////////////////////////////////////////////////////


hxl_proxy.ui = {};


/**
 * Set up the forms for recipe filters.
 *
 * @param form_node The node of the <form> element containing the filters.
 */
hxl_proxy.ui.setup_filters = function (form_node) {

    /**
     * Set up the form for a single recipe filter.
     */
    function setup_filter_form(node, index) {
        var field_types = "input,select,textarea"

        // Grab info from the (possibly hidden) select element
        var filter_name = $(node).find(".field_filter select").val();
        var filter_desc = $(node).find(".field_filter option:selected").text();
        var filter_class = ".filter-" + filter_name;

        // Hide all filters, then show the currently-chosen one
        $(node).find(".filter-body").hide();
        $(node).find(".filter-body").find(field_types).prop("disabled", true);
        $(node).find(filter_class).show();
        $(node).find(filter_class).find(field_types).prop("disabled", false);
    };

    // Set up the new-filter form on the recipe page
    $(form_node).find(".filter-new").each(function (index) {
        var filter_node = this;
        setup_filter_form(filter_node, index);
        // Reconfigure form view when the type selector changes
        $(filter_node).find(".field_filter select").on("change", function () {
            setup_filter_form(filter_node, index);
        })
    });

    // Set up aggregate fields for the count filter
    $(form_node).find(".filter-count .aggregate").each(function (index) {
        function setup (container_node, select_node) {
            var aggregate_type = select_node.val();
            var header_node, column_node;
            if (!aggregate_type) {
                container_node.find('.aggregate-pattern').hide().find('input').attr('required', false);
                header_node = container_node.find('.aggregate-header').hide().find('input');
                column_node = container_node.find('.aggregate-column').hide().find('input').attr('required', false);
            } else if (aggregate_type == 'count') {
                container_node.find('.aggregate-pattern').hide().find('input').attr('required', false);
                header_node = container_node.find('.aggregate-header').show().find('input');
                column_node = container_node.find('.aggregate-column').show().find('input').attr('required', true);
            } else {
                var title = aggregate_type.slice(0, 1).toUpperCase() + aggregate_type.slice(1);
                container_node.find('.aggregate-pattern').show().find('input').attr('required', true);
                header_node = container_node.find('.aggregate-header').show().find('input');
                column_node = container_node.find('.aggregate-column').show().find('input').attr('required', true);
            }
            // provide default values, if needed
            if (aggregate_type) {
                var title = aggregate_type.slice(0, 1).toUpperCase() + aggregate_type.slice(1);
                if (!header_node.attr('value')) {
                    header_node.attr('value', title);
                }
                if (!column_node.attr('value')) {
                    column_node.attr('value', '#meta+' + aggregate_type);
                }
            }
        }
        var container_node = $(this);
        var select_node = container_node.find('select');
        setup(container_node, select_node);
        select_node.on("change", function (event) {
            setup(container_node, select_node);
            return true;
        });
    });
};


/**
 * Trim empty fields from a form before submitting.
 * TODO: needs to be able to handle failed validation.
 */
hxl_proxy.ui.trimForm = function (contextNode) {
    $(contextNode).find(":input").filter(function () {
        return !this.value;
    }).attr("disabled", "disabled");
    return true; // ensure form still submits
};


/**
 * Trim unused fields from the tagger.
 */
hxl_proxy.ui.trimTagger = function (formNode) {
    for (var i = 1; i < 100; i++) {
        var baseName = "tagger-" + hxl_proxy.util.pad2(i);
        var headerNode = $(formNode).find("input[name='" + baseName + "-header']");
        var tagNode = $(formNode).find("input[name='" + baseName + "-tag']");
        if (!tagNode.val()) {
            headerNode.attr("disabled", "disabled");
            tagNode.attr("disabled", "disabled");
        }
    }
    return true;
};


/**
 * Add a field in a list.
 */
hxl_proxy.ui.addField = function (contextNode) {
    var lastInputNode = $(contextNode).siblings('input').last();
    var newInputNode = $(lastInputNode).clone(true);
    var parts = hxl_proxy.util.parseFieldName($(lastInputNode).attr('name'));
    if (parts[2]) {
        parts[2]++;
        var name = hxl_proxy.util.makeFieldName(parts);
        $(newInputNode).attr('name', name).attr('value', '').insertAfter(lastInputNode);
    }
};


/**
 * Event handler: renumber HTML markup for a filter list and submit.
 * Event handler for the sortable JS library.
 */
hxl_proxy.ui.resortFilterForms = function (event, ui) {
    $(event.target.childNodes).filter('.filter').each(hxl_proxy.ui.renumberFilterForm);
    $(event.target.childNodes).closest('form').submit();
};


/**
 * Renumber HTML markup for a filter form (including all fields).
 * @param index The zero-based index in the new order (will be converted to 1-based).
 * @param filterNode The root node of the tree to renumber.
 */
hxl_proxy.ui.renumberFilterForm = function (index, filterNode) {
    $(filterNode).find('*').each(function (i, formNode) {
        $.each(['name', 'for', 'id'], function (i, name) {
            var oldValue = $(formNode).attr(name);
            if (oldValue) {
                var newValue = oldValue.replace(/\d\d/, hxl_proxy.util.pad2(index + 1));
                if (oldValue != newValue) {
                    $(formNode).attr(name, newValue);
                }
            }
        });
    });
};


/**
 * Remove a filter from the form.
 */
hxl_proxy.ui.removeFilter = function (node) {
    if (confirm("Remove filter?")) {
        var form = $(node).closest('form');
        $(node).closest("li").remove();
        form.find('.filter').each(hxl_proxy.ui.renumberFilterForm);
        form.submit();
    }
    return false;
};


/**
 * Renumber subitems in a form section.
 * @param container: The container node
 * @param selector: The selector for the items to renumber.
 */
hxl_proxy.ui.renumberFormItems = function (container, selector) {
    // Form attributes to be renumbered
    var atts = ['id', 'name', 'for'];

    // Iterate over just the items to get the count
    $(container).find(selector).each(function (index, item) {

        // Renumber everything inside each item with the item number (+1)
        $(item).find('*').addBack().each(function (i, node) {
            for (i in atts) {
                var name = atts[i];
                var value = $(node).attr(name);
                if (value && value.match(/-[0-9][0-9]$/)) {
                    var parts = hxl_proxy.util.parseFieldName(value);
                    $(node).attr(name, hxl_proxy.util.makeFieldName([parts[0], parts[1], index + 1]));
                }
            }
        });
    });
};


/**
 * Duplicate a form item (repeatable field or section).
 * @param node The node to duplicate (new copy will be right after).
 * @param container_selector JQuery selector for the container node.
 * @param item_selector JQuery selector for the repeatable items (usually a class).
 */
hxl_proxy.ui.duplicate = function (node, container_selector, item_selector) {
    var new_node = $(node).clone();
    $(new_node).find('input[value],textarea[value]').attr('value', '');
    $(node).after(new_node);
    hxl_proxy.ui.renumberFormItems($(node).closest(container_selector), item_selector);
    hxl_proxy.ui.setup_filters($(node).closest('form'));
};


/**
 * Delete a form item (repeatable field or section).
 * @param node The node to delete.
 * @param container_selector JQuery selector for the container node.
 * @param item_selector JQuery selector for the repeatable items (usually a class)
 */
hxl_proxy.ui.delete = function (node, container_selector, item_selector) {
    var container = $(node).closest(container_selector);
    if ($(container).find(item_selector).length > 1) {
        if (confirm("Remove item?")) {
            $(node).remove();
            hxl_proxy.ui.renumberFormItems(container, item_selector);
        }
    } else {
        alert("Can't remove last item.");
    }
};


////////////////////////////////////////////////////////////////////////
// Utility functions.
////////////////////////////////////////////////////////////////////////


hxl_proxy.util = {};


/**
 * Left 0-pad an integer to two places.
 * @param num The integer to pad.
 * @return Two-character string representation, zero-padded.
 */
hxl_proxy.util.pad2 = function (num) {
    return ('00' + num).substr(-2);
    var s = num+"";
    while (s.length < size) s = "0" + s;
    return s;
};


/**
 * Parse the name of a sequentially-numbered field
 */
hxl_proxy.util.parseFieldName = function (name) {

    // try double numbering first
    var result = /^(.+)([0-9][0-9])-([0-9][0-9])$/.exec(name);
    if (result) {
        return [result[1], parseInt(result[2]), parseInt(result[3])]
    }

    // now try single numbering
    result = /^(.+)([0-9][0-9])$/.exec(name);
    if (result) {
        return [result[1], parseInt(result[2])];
    }

    // field is not numbered
    return [name];
};


/**
 * Construct a sequential field name from its parts.
 */
hxl_proxy.util.makeFieldName = function (parts) {
    var name = parts[0];

    if (parts[1]) {
        name += hxl_proxy.util.pad2(parts[1]);
    }

    if (parts[2]) {
        name += '-' + hxl_proxy.util.pad2(parts[2]);
    }

    return name;
};


////////////////////////////////////////////////////////////////////////
// Run startup code.
////////////////////////////////////////////////////////////////////////


// For all forms with the class "autotrim", disable any fields with empty values
$(function() {
    $("form.autotrim").submit(function() {
        $(this).find(":input").filter(function(){ return !this.value; }).attr("disabled", "disabled");
        return true; // ensure form still submits
    });
});


// Trim empty elements from forms on submission.
$(function() {
    $("form").submit(function() { hxl_proxy.ui.trimForm(this); });
});


// Trim unused rows from the tagger form
$(function() {
    $("form.tagger").submit(function () { hxl_proxy.ui.trimTagger(this); });
});


// end
