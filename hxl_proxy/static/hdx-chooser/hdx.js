/**
 * Client-side code for the HDX chooser.
 */

// Base object/namespace
var hdx = {};

// Set the URL if not already assigned
if (!hdx.chooserURL) {
    hdx.chooserURL = 'http://davidmegginson.github.io/hdx-chooser/hdx-chooser.html';
}

/**
 * Activate the chooser.
 *
 * The callback will receive a CKAN resource object if the selection
 * is successful.  The resource URL is in the .url property.
 *
 * Example:
 * <pre>
 * hdx.choose(function (resource) {
 *   alert("The user choose " + resource.url);
 * });
 * </pre>
 *
 * @param callback The callback function to receive the JavaScript resource.
 */
hdx.choose = function(callback) {
    hdx.callback = callback;
    hdx.popup = window.open(hdx.chooserURL, 'HDX dataset chooser', 'dialog,dependent');
    window.addEventListener('focus', hdx.close, true);
};


/**
 * Function to close the popup if it exists.
 *
 * Use this as a focus handler on the parent window, to hide the popup
 * if the user clicks or taps outside it.  Removes itself as a listener.
 */
hdx.close = function() {
    window.removeEventListener('focus', hdx.close, true);
    if (hdx.popup) {
        hdx.popup.close();
        hdx.popup = null;
    }
};

/**
 * Function to react to a message from the popup.
 *
 * Checks that the message is from the popup before acting.
 *
 * @param event The message event. The HDX resource is in the .data
 * property.
 */
hdx.handleSelection = function(event) {
    if (event.source == hdx.popup) {
        window.removeEventListener('message', hdx.handleSelection, true);
        hdx.popup.close();
        hdx.popup = null;
        hdx.callback(event.data);
    }
};


//
// Listen for a selection message from the child window.
//
window.addEventListener('message', hdx.handleSelection);

// end
