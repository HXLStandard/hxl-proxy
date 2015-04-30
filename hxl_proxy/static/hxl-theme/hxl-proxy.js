/**
 * Root object for all HXL Proxy functions and variables.
 */
var hxl_proxy = {}

hxl_proxy.setup_fieldset = function(node, index) {
    filter_name = $(node).find(".field_filter select").val();
    filter_class = ".fields-" + filter_name;
    filter_title = "" + (index + 1) + ": " + (filter_name ? filter_name : '(not set)');
    $(node).find(".modal-title").text(filter_title);

    var filter_button = $(node).find(".filter-button");
    filter_button.text(filter_title);
    if (filter_name) {
        filter_button.removeClass("btn-default")
        filter_button.addClass("btn-primary")
    } else {
        filter_button.removeClass("btn-primary")
        filter_button.addClass("btn-default")
    }
    $(node).find(".hideable").hide();
    $(node).find(".hideable").find(hxl_proxy.field_types).prop("disabled", true);
    $(node).find(filter_class).show();
    $(node).find(filter_class).find(hxl_proxy.field_types).prop("disabled", false);
};

hxl_proxy.prepare_form = function() {
    hxl_proxy.field_types = "input,select"
    $(".hideable").hide();
    $("#filter-form div.filter").each(function (index) {
        var filter_node = this;
        hxl_proxy.setup_fieldset(filter_node, index);
        $(filter_node).find(".field_filter select").on("change", function () {
            hxl_proxy.setup_fieldset(filter_node, index);
        })
    });
};
