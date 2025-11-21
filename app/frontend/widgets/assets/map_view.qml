import QtQuick 2.15
import QtWebView 1.3

Item {
    WebView {
        id: webView
        anchors.fill: parent
        url: offlineMapUrl
        Component.onCompleted: console.log("WebView loaded", url)
    }
}
