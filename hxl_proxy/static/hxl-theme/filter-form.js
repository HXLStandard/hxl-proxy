// Hide all hideable fields
$(".hideable").hide();

var field_types = "input,select";

function setup_fieldset(node) {
    filter_name = $(node).find(".field_filter select").val();
    filter_class = ".fields-" + filter_name;
    $(node).find(".hideable").hide();
    $(node).find(".hideable").find(field_types).prop("disabled", true);
    $(node).find(filter_class).show();
    $(node).find(filter_class).find(field_types).prop("disabled", false);
}

// Add triggers to hide/show fields based on filter
$("#filter-form fieldset").each(function (index) {
    var filter_node = this;
    setup_fieldset(filter_node);
    $(filter_node).find(".field_filter select").on("change", function () {
        setup_fieldset(filter_node);
    })
});
