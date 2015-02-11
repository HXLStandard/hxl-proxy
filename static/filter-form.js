// Hide all hideable fields
$(".hideable").hide();

function setup_fieldset(node) {
    filter_name = $(node).find(".field_filter select").val();
    $(node).find(".hideable").hide();
    $(node).find(".filter_field_" + filter_name).show();
}

// Add triggers to hide/show fields based on filter
$("#filter-form fieldset").each(function (index) {
    var filter_node = this;
    setup_fieldset(filter_node);
    $(filter_node).find(".field_filter select").on("change", function () {
        setup_fieldset(filter_node);
    })
});
