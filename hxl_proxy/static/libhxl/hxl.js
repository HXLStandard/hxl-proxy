/**
 * Simple HXL library.
 *
 * This isn't a full-featured HXL library; it focusses on datasets
 * that have already had tags expanded, and includes mainly filtering
 * operations that are useful to support mapping and visualisation.
 *
 * @author David Megginson
 * @date Started 2015-02
 */

////////////////////////////////////////////////////////////////////////
// Root object
////////////////////////////////////////////////////////////////////////

/**
 * Root hxl object, from which everything else starts.
 */
var hxl = {
    classes: {},
    loggers: []
};

/**
 * Log a warning or error message.
 *
 * Add logger functions to hxl.loggers.
 *
 * @param message The message to log.
 */
hxl.log = function (message) {
    hxl.loggers.forEach(function (logger) {
        loggers(message);
    });
};

/**
 * Wrap a JavaScript array as a HXL dataset.
 */
hxl.wrap = function (rawData) {
    return new hxl.classes.Dataset(rawData);
};

/**
 * Load a remote HXL dataset asynchronously.
 *
 * The callback takes a single argument, which is
 * the HXL data source (when successfully loaded).
 *
 * @param url The URL of the HXL dataset to load.
 * @param callback The function to call when loaded.
 */
hxl.load = function (url, callback) {
    if (typeof(Papa) != 'undefined' && typeof(Papa.parse) != 'undefined') {
        Papa.parse(url, {
            download: true,
            skipEmptyLines: true,
            complete: function (result) {
                callback(hxl.wrap(result.data));
            },
            error: function (result) {
                throw new Error(result.errors.join("\n"));
            }
        });
    } else {
        throw Error("No CSV parser available (tried Papa.parse)");
    }
};

/**
 * Normalise case and whitespace in a string.
 */
hxl.norm = function (value) {
    if (value) {
        return value.toString().trim().replace(/\s+/, ' ').toLowerCase();
    } else {
        return null;
    }
};


////////////////////////////////////////////////////////////////////////
// hxl.classes.Source
////////////////////////////////////////////////////////////////////////

/**
 * Abstract base class for any HXL data source.
 * Derived classes must define getColumns() and iterator()
 */
hxl.classes.Source = function() {
    var prototype = Object.getPrototypeOf(this);
    Object.defineProperty(this, 'columns', {
        enumerable: true,
        get: prototype.getColumns
    });
    Object.defineProperty(this, 'rows', {
        enumerable: true,
        get: prototype.getRows
    });
    Object.defineProperty(this, 'headers', {
        enumerable: true,
        get: prototype.getHeaders
    });
    Object.defineProperty(this, 'tags', {
        enumerable: true,
        get: prototype.getTags
    });
    Object.defineProperty(this, 'displayTags', {
        enumerable: true,
        get: prototype.getDisplayTags
    });
}

/**
 * Get an array of row objects.
 *
 * This method might be highly inefficient, depending on the
 * implementation in the derived class. Normally, it's best
 * to go through the rows using an iterator.
 *
 * @return An array of hxl.classes.Row objects.
 */
hxl.classes.Source.prototype.getRows = function () {
    var row;
    var rows = [];
    var iterator = this.iterator();
    while (row = iterator.next()) {
        rows.push(row);
    }
    return rows;
}

/**
 * Get an array of string headers.
 */
hxl.classes.Source.prototype.getHeaders = function () {
    return this.columns.map(function (col) { return col.header; });
}

/**
 * Get an array of tags.
 */
hxl.classes.Source.prototype.getTags = function () {
    return this.columns.map(function (col) { return col.tag; });
}

/**
 * Get an array of tagspecs.
 */
hxl.classes.Source.prototype.getDisplayTags = function () {
    return this.columns.map(function (col) { return col.displayTag; });
}

/**
 * Get the minimum value for a column
 */
hxl.classes.Source.prototype.getMin = function(pattern) {
    var min, row, value;
    var iterator = this.iterator();
    var pattern = hxl.classes.Pattern.parse(pattern); // more efficient to precompile
    while (row = iterator.next()) {
        value = row.get(pattern);
        if (min === null || (value !== null && value < min)) {
            min = value;
        }
    }
    return min;
}

/**
 * Get the minimum value for a column
 */
hxl.classes.Source.prototype.getMax = function(pattern) {
    var max, row, value;
    var iterator = this.iterator();

    pattern = hxl.classes.Pattern.parse(pattern); // more efficient to precompile
    while (row = iterator.next()) {
        value = row.get(pattern);
        if (max === null || (value !== null && value > max)) {
            max = value;
        }
    }
    return max;
}

/**
 * Get a list of unique values for a tag
 */
hxl.classes.Source.prototype.getValues = function(pattern) {
    var row;
    var iterator = this.iterator();
    var value_map = {};

    pattern = hxl.classes.Pattern.parse(pattern); // more efficient to precompile
    while (row = iterator.next()) {
        value_map[row.get(pattern)] = true;
    }
    return Object.keys(value_map);
}

/**
 * Check if a dataset contains at least one column matching a pattern.
 */
hxl.classes.Source.prototype.hasColumn = function (pattern) {
    var pattern = hxl.classes.Pattern.parse(pattern); // more efficient to precompile
    this.getColumns().forEach(function (col) {
        if (pattern.match(col)) {
            return true;
        }
    });
    return false;
}

/**
 * Get a list of indices for columns matching a tag pattern.
 */
hxl.classes.Source.prototype.getMatchingColumns = function(pattern) {
    var result = [];
    var pattern = hxl.classes.Pattern.parse(pattern); // more efficient to precompile
    this.getColumns().forEach(function (col) {
        if (pattern.match(col)) {
            result.push(col);
        }
    });
    return result;
}

/**
 * Fire a callback on each row of data.
 *
 * The callback has the form
 *
 * function (row, source, rowNumber) {}
 *
 * (Often, the callback will need to bother with only the first parameter,
 * so function (row) {} will be more typical).
 *
 * @param callback function that will get called for each row of data.
 * @return the number of rows processed.
 */
hxl.classes.Source.prototype.each = function(callback) {
    var row, rowNumber = 0, iterator = this.iterator();
    while (row = iterator.next()) {
        callback(row, this, rowNumber++);
    }
    return rowNumber;
}

/**
 * Alias each() to forEach()
 */
hxl.classes.Source.prototype.forEach = hxl.classes.Source.prototype.each;

/**
 * Test if a tag pattern points mainly to numbers.
 *
 * @param pattern The tag pattern to test.
 * @return true if at least 90% of the non-null values are numeric.
 */
hxl.classes.Source.prototype.isNumbery = function(pattern) {
    var total_seen = 0;
    var numeric_seen = 0;
    this.getValues(pattern).forEach(function (value) {
        if (value) {
            total_seen++;
            if (!isNaN(value)) {
                numeric_seen++;
            }
        }
    });
    return (total_seen > 0 && (numeric_seen/total_seen >= 0.9));;
}

/**
 * Filter rows to include only those that match at least one predicate.
 *
 * @param predicates a list of predicates.  See
 * hxl.classes.RowFilter for details.
 * @return a new data source, including only selected data rows.
 */
hxl.classes.Source.prototype.withRows = function(predicates) {
    return new hxl.classes.RowFilter(this, predicates, false);
}

/**
 * Filter rows to include only those that match none of the predicates.
 *
 * @param predicates a list of predicates.  See
 * hxl.classes.RowFilter for details.
 * @return a new data source, excluding matching data rows.
 */
hxl.classes.Source.prototype.withoutRows = function(predicates) {
    return new hxl.classes.RowFilter(this, predicates, true);
}

/**
 * Return this data source wrapped in a hxl.classes.ColumnFilter
 *
 * @param patterns a list of tag patterns for included columns (whitelist).
 * @return a new data source, including only matching columns.
 */
hxl.classes.Source.prototype.withColumns = function(patterns) {
    return new hxl.classes.ColumnFilter(this, patterns);
}

/**
 * Return this data source wrapped in a hxl.classes.ColumnFilter
 *
 * @param patterns a list of tag patterns for excluded columns (blacklist).
 * @return a new data source, excluding matching columns.
 */
hxl.classes.Source.prototype.withoutColumns = function(patterns) {
    return new hxl.classes.ColumnFilter(this, patterns, true);
}

/**
 * Return this data source wrapped in a hxl.classes.CountFilter
 *
 * @param patterns a list of tag patterns for which to count the
 * unique combinations 
 * @param aggregate (optional) a single numeric tag pattern for which
 * to produce aggregate values
 * @return a new data source, including the aggregated data.
 */
hxl.classes.Source.prototype.count = function(patterns, aggregate) {
    return new hxl.classes.CountFilter(this, patterns, aggregate);
}

/**
 * Return this data source wrapped in a hxl.classes.RenameFilter
 *
 * @param pattern the tag pattern to match for replacement.
 * @param newTag the new HXL tag spec (e.g. "#adm1+code").
 * @param newHeader (optional) the new header. If undefined, don't change.
 * @param index the zero-based index to replace among matching tags. If undefined,
 * replace *all* matches.
 * @return a new data source, with matching column(s) replaced.
 */
hxl.classes.Source.prototype.rename = function(pattern, newTag, newHeader, index) {
    return new hxl.classes.RenameFilter(this, pattern, newTag, newHeader, index);
}

/**
 * Return the data source wrapped in a hxl.classes.CacheFilter
 *
 * @return a new data source, with all transformations cached.
 */
hxl.classes.Source.prototype.cache = function() {
    return new hxl.classes.CacheFilter(this);
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.Dataset
////////////////////////////////////////////////////////////////////////

/**
 * An original HXL dataset (including the raw data)
 * Derived from hxl.classes.Source
 */
hxl.classes.Dataset = function (rawData) {
    hxl.classes.Source.call(this);
    this._rawData = rawData;
    this._tagRowIndex = null;
    this._savedColumns = null;
}

hxl.classes.Dataset.prototype = Object.create(hxl.classes.Source.prototype);
hxl.classes.Dataset.prototype.constructor = hxl.classes.Dataset;

/**
 * Get an array of column definitions.
 */
hxl.classes.Dataset.prototype.getColumns = function() {
    var cols, tags_index, tagspec, header;
    if (this._savedColumns == null) {
        cols = [];
        tags_index = this._getTagRowIndex();
        if (tags_index > -1) {
            for (var i = 0; i < this._rawData[tags_index].length; i++) {
                tagspec = this._rawData[tags_index][i];
                header = null;
                if (tags_index > 0) {
                    header = this._rawData[tags_index-1][i];
                }
                if (tagspec.match(/^\s*#.*/)) {
                    cols.push(hxl.classes.Column.parse(tagspec, header));
                } else {
                    cols.push(null);
                }
            }
            this._savedColumns = cols;
        } else {
            throw "No HXL hashtag row found.";
        }
    }
    return this._savedColumns;
}

/**
 * Get an iterator through all the rows in the dataset.
 */
hxl.classes.Dataset.prototype.iterator = function() {
    var index = this._getTagRowIndex() + 1;
    var columns = this.columns;
    var rawData = this._rawData;
    return {
        next: function() {
            if (index < rawData.length) {
                return new hxl.classes.Row(rawData[index++], columns);
            } else {
                return null;
            }
        }
    };
}

/**
 * Get the index of the tag row.
 */
hxl.classes.Dataset.prototype._getTagRowIndex = function() {
    var i;
    if (this._tagRowIndex == null) {
        for (i = 0; i < 25 && i < this._rawData.length; i++) {
            if (this._isTagRow(this._rawData[i])) {
                this._tagRowIndex = i;
                return this._tagRowIndex;
            }
        }
        throw "No HXL tag row found."
    } else {
        return this._tagRowIndex;
    }
}

/**
 * Test a candidate HXL tag row.
 *
 * @param rawRow a raw array of values (e.g. a CSV row).
 * @return true if this qualifies as a tag row.
 */
hxl.classes.Dataset.prototype._isTagRow = function(rawRow) {
    var seenTag = false, seenNonTag = false;
    rawRow.forEach(function (rawValue) {
        if (rawValue) {
            if (rawValue.match(/^\s*#.*$/) && hxl.classes.Pattern.parse(rawValue)) {
                seenTag = true;
            } else {
                seenNonTag = true;
            }
        }
    });
    return (seenTag && !seenNonTag);
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.Column
////////////////////////////////////////////////////////////////////////

/**
 * Wrapper for a HXL column definition.
 */
hxl.classes.Column = function (tag, attributes, header) {
    this.tag = tag;
    this.attributes = attributes;
    this.header = header;
    Object.defineProperty(this, 'displayTag', {
        enumerable: true,
        get: hxl.classes.Column.prototype.getDisplayTag
    });
}

/**
 * Create a display tagspec for the column.
 */
hxl.classes.Column.prototype.getDisplayTag = function() {
    return [this.tag].concat(this.attributes.sort()).join('+');
};

/**
 * Parse a tag spec into its parts.
 */
hxl.classes.Column.parse = function(spec, header, useException) {
    var result = spec.match(/^\s*(#[A-Za-z][A-Za-z0-9_]*)((\s*\+[A-Za-z][A-Za-z0-9_]*)*)?\s*$/);
    var attributes = [];
    if (result) {
        if (result[2]) {
            // filter out empty values
            attributes = result[2].split(/\s*\+/).filter(function(attribute) { return attribute; });
        }
        return new hxl.classes.Column(result[1], attributes, header);
    } else if (useException) {
        throw "Bad tag specification: " + spec;
    } else {
        hxl.log("Bad tag specification: " + spec);
        return null;
    }
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.Pattern
////////////////////////////////////////////////////////////////////////

/**
 * Wrapper for a HXL column definition.
 */
hxl.classes.Pattern = function (tag, include_attributes, exclude_attributes) {
    this.tag = tag;
    this.include_attributes = include_attributes;
    this.exclude_attributes = exclude_attributes;
}

hxl.classes.Pattern.prototype.match = function(column) {
    var attribute, i;

    // tags must match
    if (this.tag != column.tag) {
        return false;
    }

    // include attributes must be present
    for (i = 0; i < this.include_attributes.length; i++) {
        attribute = this.include_attributes[i];
        if (column.attributes.indexOf(attribute) < 0) {
            return false;
        }
    }

    // exclude attributes must not be present
    for (i = 0; i < this.exclude_attributes.length; i++) {
        attribute = this.exclude_attributes[i];
        if (column.attributes.indexOf(attribute) > -1) {
            return false;
        }
    }

    return true;
}

/**
 * Parse a string into a tag pattern.
 *
 * @param pattern a tag-pattern string, like "#org+funder-impl"
 * @param useException (optional) throw an exception on failure.
 * @return a hxl.classes.Pattern, or null if parsing fails (and useException is false).
 */
hxl.classes.Pattern.parse = function(pattern, useException) {
    var result, include_attributes, exclude_attributes, attribute_specs, i;
    if (pattern instanceof hxl.classes.Pattern) {
        // If this is already parsed, then just return it.
        return pattern;
    } else if (!pattern) {
        if (useException) {
            throw new Error("No tag pattern provided");
        } else {
            return null;
        }
    } else {
        result = pattern.match(/^\s*(#[A-Za-z][A-Za-z0-9_]*)((?:\s*[+-][A-Za-z][A-Za-z0-9_]*)*)\s*$/);
        if (result) {
            include_attributes = [];
            exclude_attributes = [];
            attribute_specs = result[2].split(/\s*([+-])/).filter(function(item) { return item; });
            for (i = 0; i < attribute_specs.length; i += 2) {
                if (attribute_specs[i] == "+") {
                    include_attributes.push(attribute_specs[i+1]);
                } else {
                    exclude_attributes.push(attribute_specs[i+1]);
                }
            }
            return new hxl.classes.Pattern(result[1], include_attributes, exclude_attributes);
        } else if (useException) {
            throw "Bad tag pattern: " + pattern;
        } else {
            hxl.log("Bad tag pattern: " + pattern);
            return null;
        }
    }
}

hxl.classes.Pattern.toString = function() {
    var s = this.tag;
    if (this.include_tags) {
        s += "+" + this.include_tags.join("+");
    }
    if (this.exclude_tags) {
        s += "-" + this.exclude_tags.join("-");
    }
    return s;
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.Row
////////////////////////////////////////////////////////////////////////

/**
 * Wrapper for a row of HXL data.
 */
hxl.classes.Row = function (values, columns) {
    this.values = values;
    this.columns = columns;
}

/**
 * Look up the first value that matches a tag pattern.
 *
 * @param pattern The tag pattern to use.
 * @return a string value, or null if none found.
 */
hxl.classes.Row.prototype.get = function(pattern) {
    var i;
    pattern = hxl.classes.Pattern.parse(pattern, true);
    for (i = 0; i < this.columns.length && i < this.values.length; i++) {
        if (pattern.match(this.columns[i])) {
            return this.values[i];
        }
    }
    return null;
}

/**
 * Look up all values that match a tag pattern.
 *
 * @param pattern The tag pattern to use.
 * @return a possibly-empty array of string values (or nulls).
 */
hxl.classes.Row.prototype.getAll = function(pattern) {
    var row = this, values = [];
    var pattern = hxl.classes.Pattern.parse(pattern, true);
    this.columns.forEach(function (column, index) {
        if (pattern.match(column)) {
            values.push(row.values[index]);
        }
    });
    return values;
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.BaseFilter (override for specific filters).
////////////////////////////////////////////////////////////////////////

hxl.classes.BaseFilter = function (source) {
    hxl.classes.Source.call(this);
    this.source = source;
}

hxl.classes.BaseFilter.prototype = Object.create(hxl.classes.Source.prototype);
hxl.classes.BaseFilter.prototype.constructor = hxl.classes.BaseFilter;

hxl.classes.BaseFilter.prototype.getColumns = function() {
    return this.source.getColumns();
}

hxl.classes.BaseFilter.prototype.iterator = function() {
    return this.source.iterator();
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.RowFilter
////////////////////////////////////////////////////////////////////////

/**
 * HXL filter class to select rows from a source.
 *
 * Usage:
 *
 * // select all rows where #adm1 is the Coastal Region
 * // *or* the population is greater than 1,000
 * var filter = new hxl.classes.RowFilter(source,
 *   { pattern: '#adm1', test: 'Coastal Region' },
 *   { pattern: '#people_num', test: function(v) { return v > 1000; } }
 * ]);
 *
 * Predicates are always "OR"'d together. If you need
 * a logical "AND", then chain another select filter.
 *
 * @param source the hxl.classes.Source
 * @param predicates a list of predicates, each of 
 * has a "test" property (and optionally, a "pattern" property).
 */
hxl.classes.RowFilter = function (source, predicates, invert) {
    hxl.classes.BaseFilter.call(this, source);
    this.predicates = this._compilePredicates(predicates);
    this.invert = invert;
}

hxl.classes.RowFilter.prototype = Object.create(hxl.classes.BaseFilter.prototype);
hxl.classes.RowFilter.prototype.constructor = hxl.classes.RowFilter;

/**
 * Override HXLFIlter.iterator to return only select rows.
 *
 * @return an iterator object that will skip rows that fail to pass at
 * least one of the predicates.
 */
hxl.classes.RowFilter.prototype.iterator = function() {
    var iterator = this.source.iterator();
    var outer = this;
    return {
        next: function() {
            var row;
            while (row = iterator.next()) {
                if (outer._tryPredicates(row)) {
                    return row;
                }
            }
            return null;
        }
    }
}

/**
 * Operator functions.
 */
hxl.classes.RowFilter.OPERATORS = {
    '=': function (a, b) { return a == b; },
    '!=': function (a, b) { return a != b; },
    '<': function (a, b) { return a < b; },
    '<=': function (a, b) { return a <= b; },
    '>': function (a, b) { return a > b; },
    '>=': function (a, b) { return a >= b; },
    '~': function (a, b) { return a.match(b); },
    '!~': function (a, b) { return !a.match(b); }
};

/**
 * Precompile the tag patterns in the predicates.
 *
 * @param predicates the predicates as input
 * @return a compiled/normalised list of predicates
 * @exception if one of the tag patterns is malformed
 */
hxl.classes.RowFilter.prototype._compilePredicates = function(predicates) {

    /**
     * Helper function: compile the tag pattern, if present
     */
    var parsePattern = function (pattern) {
        if (pattern) {
            return hxl.classes.Pattern.parse(pattern);
        } else {
            return null;
        }
    };

    /**
     * Helper function: if test is a plain string, create an equality function.
     */
    var parseTest = function (test) {
        if (typeof(test) != 'function') {
            test = hxl.norm(test);
            return function (value) { return hxl.norm(value) == test; };
        } else {
            return test;
        }
    };

    /**
     * Helper function: parse a string predicate.
     */
    var parsePredicate = function (s) {
        var operator, expected;

        // loose expression (parsing the pattern will verify)
        var result = s.match(/^\s*([^!=~<>+]+)\s*(!?[=~]|<=?|>=?)(.*)$/);
        if (result) {
            operator = hxl.classes.RowFilter.OPERATORS[result[2]];
            expected = hxl.norm(result[3]);
            return {
                pattern: parsePattern(result[1]),
                test: function (value) { return operator(hxl.norm(value), expected); }
            };
        } else {
            throw Error("Bad predicate: " + s);
        }
    };

    // If it's not a list, wrap it in one
    if (!Array.isArray(predicates)) {
        predicates = [ predicates ];
    }

    // Map the list to a compiled/normalised version
    return predicates.map(function (predicate) {
        if (typeof(predicate) == 'object') {
            return {
                pattern: parsePattern(predicate.pattern),
                test: parseTest(predicate.test)
            };
        } else if (typeof(predicate) == 'function') {
            return {
                test: predicate
            };
        } else {
            return parsePredicate(predicate);
        }
    });
}

/**
 * Return success if _any_ of the predicates succeeds.
 */
hxl.classes.RowFilter.prototype._tryPredicates = function(row) {
    var predicate;

    // Try every predicate on the row
    for (var i = 0; i < this.predicates.length; i++) {
        predicate = this.predicates[i];

        // If the first part is set, then it's a tag pattern
        // test only the values with hashtags that match
        if (predicate.pattern) {
            var values = row.getAll(predicate.pattern);
            for (var j = 0; j < values.length; j++) {
                if (predicate.test(values[i])) {
                    return !this.invert;
                }
            }
        } 

        // If the first part is not set, then it's a row predicate
        // test the whole row at once
        else {
            if (this.invert) {
                return !predicate.test(row);
            } else {
                return predicate.test(row);
            }
        }
    }

    return this.invert;
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.ColumnFilter
////////////////////////////////////////////////////////////////////////

/**
 * HXL filter class to remove columns from a dataset.
 *
 * @param source the HXL data source (may be another filter).
 * @param patterns a list of HXL tag patterns to include (or exclude).
 * @param invert if true, exclude matching columns rather than including them (blacklist).
 */
hxl.classes.ColumnFilter = function (source, patterns, invert) {
    hxl.classes.BaseFilter.call(this, source);
    this.patterns = this._compilePatterns(patterns);
    this.invert = invert;
}

hxl.classes.ColumnFilter.prototype = Object.create(hxl.classes.BaseFilter.prototype);
hxl.classes.ColumnFilter.prototype.constructor = hxl.classes.ColumnFilter;

/**
 * Override hxl.classes.BaseFilter.getColumns to return only the allowed columns.
 *
 * This method triggers lazy processing that also saves the indices for
 * slicing the data itself.
 *
 * @return a list of hxl.classes.Column objects.
 */
hxl.classes.ColumnFilter.prototype.getColumns = function() {
    if (typeof(this._savedColumns) == 'undefined') {

        /**
         * Check if any of the patterns matches the column.
         */
        var columnMatches = function(column, patterns) {
            for (var i = 0; i < patterns.length; i++) {
                if (patterns[i].match(column)) {
                    return true;
                }
            }
            return false;
        };

        // we haven't extracted the columns before, so do it now
        var newColumns = [];
        var newIndices = [];

        // check every column against the patterns
        for (var i = 0; i < this.source.columns.length; i++) {
            var is_match = columnMatches(this.source.columns[i], this.patterns);
            if ((is_match && !this.invert) || (!is_match && this.invert)) {
                newColumns.push(this.source.columns[i]);
                newIndices.push(i);
            }
        }

        // save the columns and indices for future use
        this._savedColumns = newColumns;
        this._savedIndices = newIndices;
    }

    // return the saved columns
    return this._savedColumns;
}

/**
 * Override hxl.classes.BaseFilter.iterator to get data with some columns removed.
 *
 * @return an iterator object to read the modified data rows.
 */
hxl.classes.ColumnFilter.prototype.iterator = function () {
    var outer = this;
    var iterator = this.source.iterator();
    return {
        next: function() {
            var i, values;
            var columns = outer.columns; // will trigger lazy column processing
            var row = iterator.next();
            if (row) {
                // Use the saved indices to slice values
                values = [];
                for (i = 0; i < outer._savedIndices.length; i++) {
                    values.push(row.values[outer._savedIndices[i]]);
                }
                return new hxl.classes.Row(values, columns);
            } else {
                // end of data
                return null;
            }
        }
    }
}

/**
 * Normalise and optimize the list of column patterns.
 */
hxl.classes.ColumnFilter.prototype._compilePatterns = function (patterns) {
    if (!Array.isArray(patterns)) {
        patterns = [ patterns ];
    }
    return patterns.map(function (pattern) {
        return hxl.classes.Pattern.parse(pattern);
    });
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.CountFilter
////////////////////////////////////////////////////////////////////////

/**
 * HXL filter to count and aggregate data.
 *
 * By default, this filter put out a dataset with the selected tags
 * and a new tag #count_num giving the number of times each
 * combination of values appears. If the aggregate tag pattern is
 * present, the filter will also produce a column with the sum,
 * average (mean), minimum, and maximum values for the tag, attaching
 * the attributes +sum, +avg, +min, and +max to the core tag.
 *
 * @param source the HXL data source (may be another filter).
 * @param patterns a list of tag patterns (strings or hxl.classes.Pattern
 * objects) whose values make up a shared key.
 */
hxl.classes.CountFilter = function (source, patterns, aggregate) {
    hxl.classes.BaseFilter.call(this, source);
    if (patterns) {
        if (!Array.isArray(patterns)) {
            patterns = [ patterns ];
        }
        this.patterns = patterns.map(function (pattern) { return hxl.classes.Pattern.parse(pattern, true); });
    } else {
        throw new Error("No tag patterns specified");
    }
    if (aggregate) {
        this.aggregate = hxl.classes.Pattern.parse(aggregate, true);
    } else {
        this.aggregate = null;
    }
}

hxl.classes.CountFilter.prototype = Object.create(hxl.classes.BaseFilter.prototype);
hxl.classes.CountFilter.prototype.constructor = hxl.classes.CountFilter;

/**
 * Override hxl.classes.BaseFilter.getColumns to return only the columns for the aggregation report.
 *
 * Will list the tags that match the patterns provided in the
 * constructor, as well as a #count_num tag, and aggregation tags if
 * the aggregation parameter was included.
 *
 * @return a list of hxl.classes.Column objects
 */
hxl.classes.CountFilter.prototype.getColumns = function() {
    var cols, indices, tagspec;
    if (!this._savedColumns) {
        cols = [];
        indices = [];
        for (var i = 0; i < this.source.columns.length; i++) {
            for (var j = 0; j < this.patterns.length; j++) {
                if (this.patterns[j].match(this.source.columns[i])) {
                    cols.push(this.source.columns[i]);
                    indices.push(i);
                    break;
                }
            }
        }
        cols.push(hxl.classes.Column.parse('#count_num'));
        if (this.aggregate) {
            tagspec = this.aggregate.tag;
            cols.push(hxl.classes.Column.parse(tagspec + '+sum'));
            cols.push(hxl.classes.Column.parse(tagspec + '+avg'));
            cols.push(hxl.classes.Column.parse(tagspec + '+min'));
            cols.push(hxl.classes.Column.parse(tagspec + '+max'));
        }
        this._savedColumns = cols;
        this._savedIndices = indices;
    }
    return this._savedColumns;
}

/**
 * Override hxl.classes.BaseFilter.iterator to return a set of rows with aggregated values.
 *
 * Each row represents a unique set of values and the number of times
 * it occurs.
 *
 * @return an iterator over the aggregated data.
 */
hxl.classes.CountFilter.prototype.iterator = function() {
    var columns = this.columns; // will trigger lazy column creation
    var data = this._aggregateData();
    var pos = 0;
    return {
        next: function () {
            if (pos < data.length) {
                return new hxl.classes.Row(data[pos++], columns);
            } else {
                return null;
            }
        }
    };
}

/**
 * Monster ugly function to aggregate data.
 * FIXME: can I decompose this into smaller parts?
 */
hxl.classes.CountFilter.prototype._aggregateData = function() {
    var row, key, values, value, entry, aggregates;
    var data_map = {};
    var aggregate_map = {};
    var data = [];
    var iterator = this.source.iterator();

    // Make a unique map of data values
    while (row = iterator.next()) {
        key = this._makeKey(row);

        // Always do a count
        if (data_map[key]) {
            data_map[key] += 1;
        } else {
            data_map[key] = 1;
        }

        // Aggregate numeric values if requested
        if (this.aggregate) {
            // try parsing, and proceed only if it's numeric
            value = parseFloat(row.get(this.aggregate));
            if (!isNaN(value)) {
                entry = aggregate_map[key];
                if (entry) {
                    // Not the first value
                    entry.total++;
                    entry.sum += value;
                    entry.avg = (entry.avg * (entry.total - 1) + value) / entry.total;
                    entry.min = (value < entry.min ? value : entry.min);
                    entry.max = (value > entry.max ? value : entry.max);
                } else {
                    // the first value
                    aggregate_map[key] = {
                        total: 1,
                        sum: value,
                        avg: value,
                        min: value,
                        max: value
                    }
                }
            }
        }
    }

    // Generate the data from the map
    for (key in data_map) {

        // Retrieve the values from the key
        values = key.split("\0");

        // Add the count
        values.push(data_map[key]);

        // Add other aggregates if requested
        if (this.aggregate) {
            entry = aggregate_map[key];
            if (entry) {
                values = values.concat([
                    entry.sum,
                    entry.avg,
                    entry.min,
                    entry.max
                ]);
            } else {
                values = values.concat([
                    '', '', '', ''
                ]);
            }
        }

        // Row is finished.
        data.push(values);
    }

    // return all the rows
    return data;
}

/**
 * Construct a unique key from the requested values in a row of data.
 *
 * @return the unique key as a single string.
 */
hxl.classes.CountFilter.prototype._makeKey = function(row) {
    var i, index;
    var values = [];
    for (i = 0; i < this._savedIndices.length; i++) {
        values.push(row.values[this._savedIndices[i]]);
    }
    return values.join("\0");
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.RenameFilter
////////////////////////////////////////////////////////////////////////

/**
 * HXL filter to rename a column (new header and tag).
 *
 * @param source the hxl.classes.Source
 * @param pattern the tag pattern to replace
 * @param newTag the new HXL tag (with attributes)
 * @param newHeader (optional) the new text header. If undefined or
 * null or false, don't change the existing header.
 * @param index the zero-based index of the match to replace. If
 * undefined or null or false, replace *all* matches.
 */
hxl.classes.RenameFilter = function (source, pattern, newTagspec, newHeader, index) {
    hxl.classes.BaseFilter.call(this, source);
    this.pattern = hxl.classes.Pattern.parse(pattern);
    this.newTagspec = newTagspec;
    this.newHeader = newHeader;
    this.index = index;
    this._savedColumns = undefined;
}

hxl.classes.RenameFilter.prototype = Object.create(hxl.classes.BaseFilter.prototype);
hxl.classes.RenameFilter.prototype.constructor = hxl.classes.RenameFilter;

/**
 * Get the renamed columns.
 */
hxl.classes.RenameFilter.prototype.getColumns = function() {
    var cols, header;
    var pattern = this.pattern;
    var tagspec = this.newTagspec;
    var index = this.index;
    if (this._savedColumns === undefined) {
        cols = [];
        // loop through the columns, translating as needed
        this.source.getColumns().forEach(function (col) {
            // Index has to be 0 or undefined for a match
            if (pattern.match(col) && !index) {
                // we have a match!
                if (this.header === undefined) {
                    header = col.header;
                } else {
                    header = this.header;
                }
                col = hxl.classes.Column.parse(tagspec, header);
                cols.push(col);
            } else {
                // no match: use existing column
                cols.push(col);
            }
            // decrement the index counter if present
            if (index) {
                index -= 1;
            }
        });
        this._savedColumns = cols;
    }
    return this._savedColumns;
}


////////////////////////////////////////////////////////////////////////
// hxl.classes.CacheFilter
////////////////////////////////////////////////////////////////////////

/**
 * HXL filter to save a copy of a transformed HXL dataset.
 *
 * This filter stops the chain, so that any future requests won't
 * go back and repeat earlier transformations. You should use it
 * when there are some expensive operations earlier in the chain
 * that you don't want to repeat.
 *
 * @param source the hxl.classes.Source
 */
hxl.classes.CacheFilter = function (source) {
    hxl.classes.BaseFilter.call(this, source);
    this._savedColumns = undefined;
    this._savedRows = undefined;
}

hxl.classes.CacheFilter.prototype = Object.create(hxl.classes.BaseFilter.prototype);
hxl.classes.CacheFilter.prototype.constructor = hxl.classes.CacheFilter;

hxl.classes.CacheFilter.prototype.getColumns = function() {
    if (this._savedColumns === undefined) {
        this._savedColumns = this.source.getColumns();
    }
    return this._savedColumns;
}

hxl.classes.CacheFilter.prototype.iterator = function() {
    var index = 0;
    if (this._savedRows === undefined) {
        this._savedRows = this.source.getRows();
    }
    return {
        next: function() {
            if (index < this._savedRows.length) {
                return this._savedRows[index++];
            } else {
                return null;
            }
        }
    };
}


// end
