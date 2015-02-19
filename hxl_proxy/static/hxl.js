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
// HXLDataset class
////////////////////////////////////////////////////////////////////////

/**
 * Top-level wrapper for a HXL dataset.
 */
function HXLDataset(rawData) {
    this._rawData = rawData;
    this._tagRowIndex = null;
    this._savedColumns = null;
    Object.defineProperty(this, 'headers', {
        enumerable: true,
        get: HXLDataset.prototype.getHeaders
    });
    Object.defineProperty(this, 'tags', {
        enumerable: true,
        get: HXLDataset.prototype.getTags
    });
    Object.defineProperty(this, 'columns', {
        enumerable: true,
        get: HXLDataset.prototype.getColumns
    });
}

/**
 * Get an array of string headers.
 */
HXLDataset.prototype.getHeaders = function () {
    index = this._getTagRowIndex();
    if (index > 0) {
        return this._rawData[index - 1];
    } else {
        return [];
    }
}

/**
 * Get an array of tags.
 */
HXLDataset.prototype.getTags = function () {
    return this._rawData[this._getTagRowIndex()];
}

/**
 * Get an array of column definitions.
 */
HXLDataset.prototype.getColumns = function() {
    if (this._savedColumns == null) {
        this._savedColumns = [];
        for (var i = 0; i < this.tags.length; i++) {
            tag = this.tags[i];
            header = null;
            if (i < this.headers.length) {
                header = this.headers[i];
            }
            this._savedColumns.push(new HXLColumn(tag, header));
        }
    }
    return this._savedColumns;
}

/**
 * Get an iterator through all the rows in the dataset.
 */
HXLDataset.prototype.iterator = function() {
    var index = this._getTagRowIndex() + 1;
    var columns = this.columns;
    var rawData = this._rawData;
    return {
        next: function() {
            if (index < rawData.length) {
                return new HXLRow(rawData[index++], columns);
            } else {
                return null;
            }
        }
    };
}

/**
 * Get the index of the tag row.
 */
HXLDataset.prototype._getTagRowIndex = function() {
    if (this._tagRowIndex == null) {
        for (var i = 0; i < 25 && i < this._rawData.length; i++) {
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

HXLDataset.prototype._isTagRow = function(row) {
    var seenTag = false;
    for (var i = 0; i < row.length; i++) {
        if (row[i]) {
            if (row[i][0] == '#') {
                seenTag = true;
            } else {
                return false;
            }
        }
    }
    return seenTag;
}

////////////////////////////////////////////////////////////////////////
// HXLColumn class
////////////////////////////////////////////////////////////////////////

/**
 * Wrapper for a HXL column definition.
 */
function HXLColumn(tag, header) {
    this.tag = tag;
    this.header = header;
}


////////////////////////////////////////////////////////////////////////
// HXLRow class
////////////////////////////////////////////////////////////////////////

/**
 * Wrapper for a row of HXL data.
 */
function HXLRow(values, columns) {
    this.values = values;
    this.columns = columns;
}

/**
 * Look up a value by tag.
 */
HXLRow.prototype.get = function(tag) {
    for (var i = 0; i < this.columns.length && i < this.values.length; i++) {
        if (this.columns[i].tag == tag) {
            return this.values[i];
        }
    }
    return null;
}

/**
 * Look up all values with a specific tag.
 */
HXLRow.prototype.getAll = function(tag) {
    values = [];
    for (var i = 0; i < this.columns.length && i < this.values.length; i++) {
        if (this.columns[i].tag == tag) {
            values.push(this.values[i]);
        }
    }
    return values;
}

////////////////////////////////////////////////////////////////////////
// HXLFilter base class (override for specific filters).
////////////////////////////////////////////////////////////////////////

function HXLFilter(dataset) {
    this.dataset = dataset;
    Object.defineProperty(this, 'headers', {
        enumerable: true,
        get: HXLDataset.prototype.getHeaders
    });
    Object.defineProperty(this, 'tags', {
        enumerable: true,
        get: HXLDataset.prototype.getTags
    });
    Object.defineProperty(this, 'columns', {
        enumerable: true,
        get: HXLDataset.prototype.getColumns
    });
}

HXLFilter.prototype.getHeaders = function() {
    return this.dataset.getHeaders();
}

HXLFilter.prototype.getTags = function() {
    return this.dataset.getTags();
}

HXLFilter.prototype.getColumns = function() {
    return this.dataset.getColumns();
}

HXLFilter.prototype.iterator = function() {
    return this.dataset.iterator();
}
