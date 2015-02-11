// Hide all hideable fields
$(".hideable").hide();

// Add triggers to hide/show fields based on filter
$("#filter-form fieldset").each(function (index) {
    var filter_node = this;
    $(filter_node).find(".field_filter select").on("change", function () {
        // hide everything
        var filter_name = $(this).val();
        $(filter_node).find(".hideable").hide();
        $(filter_node).find(".filter_field_" + filter_name).show();
    })
});
