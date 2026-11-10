import QtQuick 2.15

Rectangle {
    id: root

    width: 1920
    height: 1080
    color: "#10224d"
    property int sessionIndex: sessionModel.lastIndex

    Image {
        anchors.fill: parent
        source: "file:///usr/share/backgrounds/jadevos-default-wallpaper.jpg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }

    Rectangle {
        anchors.fill: parent
        color: "#30102040"
    }

    Column {
        anchors.centerIn: parent
        width: 390
        spacing: 16

        Text {
            width: parent.width
            text: "JadevOS"
            color: "white"
            font.pixelSize: 44
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            width: parent.width
            text: "COMPUTERS  |  BETA 4"
            color: "#bdece1"
            font.pixelSize: 14
            font.letterSpacing: 2
            horizontalAlignment: Text.AlignHCenter
        }

        Rectangle {
            width: parent.width
            height: 198
            radius: 18
            color: "#dd10224d"
            border.color: "#70ffffff"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 12

                TextInput {
                    id: username
                    width: parent.width
                    height: 42
                    text: userModel.lastUser
                    color: "white"
                    font.pixelSize: 17
                    verticalAlignment: TextInput.AlignVCenter
                    selectByMouse: true
                    leftPadding: 12
                    onAccepted: password.forceActiveFocus()
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        x: 12
                        text: "Username"
                        color: "#bbffffff"
                        visible: username.text.length === 0
                    }
                    Rectangle {
                        anchors.fill: parent
                        z: -1
                        radius: 8
                        color: "#552d4773"
                        border.color: "#6680a8"
                    }
                }

                TextInput {
                    id: password
                    width: parent.width
                    height: 42
                    color: "white"
                    font.pixelSize: 17
                    echoMode: TextInput.Password
                    verticalAlignment: TextInput.AlignVCenter
                    selectByMouse: true
                    leftPadding: 12
                    onAccepted: sddm.login(username.text, password.text, root.sessionIndex)
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        x: 12
                        text: "Password"
                        color: "#bbffffff"
                        visible: password.text.length === 0
                    }
                    Rectangle {
                        anchors.fill: parent
                        z: -1
                        radius: 8
                        color: "#552d4773"
                        border.color: "#6680a8"
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 42
                    radius: 9
                    color: "#37bfa0"

                    Text {
                        anchors.centerIn: parent
                        text: "Sign in"
                        color: "#10224d"
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: sddm.login(username.text, password.text, root.sessionIndex)
                    }
                }
            }
        }

        Text {
            id: errorMessage
            width: parent.width
            text: ""
            color: "#ffd1d1"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            errorMessage.text = "Sign-in failed. Check your username and password."
            password.text = ""
            password.forceActiveFocus()
        }
    }

    Component.onCompleted: username.forceActiveFocus()
}
