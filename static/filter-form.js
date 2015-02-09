// Hide all hideable fields
$(".hideable").hide();

// Map of fields to show for each filter
var filter_field_map = {
    "norm": [],
    "count": [".field_tags"],
    "sort": [".field_tags", ".field_sort"],
    "cut": [".field_tags"],
    "select": [".field_query"]
};

// Add triggers to hide/show fields based on filter
$("#filter-form fieldset").each(function (index) {
    var filter_node = this
    $(filter_node).find(".field_filter select").on("change", function () {
        // hide everything
        $(filter_node).find(".hideable").hide();
        var filter_name = $(this).val();
        var fields = filter_field_map[filter_name];
        fields.forEach(function (field_class) {
            $(filter_node).find(field_class).show()
        });
    })
});
