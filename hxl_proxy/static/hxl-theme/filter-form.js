// Hide all hideable fields
$(".hideable").hide();

var field_types = "input,select";

function setup_fieldset(node, index) {
    filter_name = $(node).find(".field_filter select").val();
    filter_class = ".fields-" + filter_name;
    filter_title = "Filter #" + (index + 1) + ": " + (filter_name ? filter_name : '(not set)');
    $(node).find(".modal-title").text(filter_title);
    $(node).find(".filter-button").text(filter_title);
    $(node).find(".hideable").hide();
    $(node).find(".hideable").find(field_types).prop("disabled", true);
    $(node).find(filter_class).show();
    $(node).find(filter_class).find(field_types).prop("disabled", false);
}

// Add triggers to hide/show fields based on filter
$("#filter-form div.filter").each(function (index) {
    console.log(index);
    var filter_node = this;
    setup_fieldset(filter_node, index);
    $(filter_node).find(".field_filter select").on("change", function () {
        setup_fieldset(filter_node, index);
    })
});
