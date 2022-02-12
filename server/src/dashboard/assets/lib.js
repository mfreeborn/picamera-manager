// Based off of: https://github.com/elsampsa/websocket-mse-demo (commit cd7bd3a)
//
// This module provides the functionality for initialising a camera source and attaching it to
// an HTML Video element. It is designed to be called by a Dash clientside callback function.
//
// A mapping of camera_id -> CameraStream is maintained to keep track of which camera streams are
// active. This allows same camera_id is initialised a second time, which will replace the first
// stream e.g. when the camera settings have been updated on the server and the stream needs to
// restart with the new configuration. 

let CAMERA_STREAMS = {};

class CameraStream {
    // represents the camera stream for a single camera
    constructor(camera_id, server_ip_address, server_port) {
        this.video_id = `network-stream-player-${camera_id}`;
        this.camera_id = camera_id;
        this.server_ip_address = server_ip_address
        this.server_port = server_port
        this.fragment_queue = [];
        this.stream_started = false;
        this.ms = new MediaSource();
        this.source_buffer = undefined;
        this.video_element = document.getElementById(this.video_id);
        this.current_duration = 0;
        this.f = 0;
        this.end_time = null;

        // the websocket will be set when the media source actually opens
        this.ws = undefined;
    }

    init() {
        console.log("Initialising video player")
        let camera_stream = this
        this.ms.onsourceopen = function () {
            CameraStream.sourceOpen(camera_stream)
        };
        this.ms.onsourceended = function () { console.log("media source ended") };
        this.ms.onsourceclosed = function () { console.log("media source closed") };

        this.video_element.src = window.URL.createObjectURL(this.ms);

        // keep a global reference to this camera stream - used when displaying
        // multiple camera streams at once
        CAMERA_STREAMS[this.camera_id] = this;

        console.log(this)
        return this;
    }

    static sourceOpen(camera_stream) {
        // set up the Media Source
        // duration here is arbitray; it is just whilst the first few seconds of video buffer
        camera_stream.ms.duration = 2;

        // set up the source_buffer
        camera_stream.source_buffer = camera_stream.ms.addSourceBuffer('video/mp4; codecs="avc1.640028, mp4a.40.2"');
        camera_stream.source_buffer.mode = "sequence";
        camera_stream.source_buffer.addEventListener("updateend", function (e) {
            CameraStream.loadFragment(camera_stream);
        });

        // set up the video_element callbacks to enable smooth playing/seeking behaviour
        camera_stream.video_element.onseeking = function (e) {
            // the source buffer only maintains 90 seconds of video data, however, the seek bar
            // can't be updated to represent this. As such, it is possible to seek to a postion
            // earlier than the earliest video data in the source_buffer, at which point the video
            // will hang. When the user tries to seek back too far, this callback steps in and 
            // moves the currentTime to a valid position.
            let new_time = camera_stream.video_element.currentTime;
            let buffer_start = camera_stream.source_buffer.buffered.start(0);
            if (new_time < buffer_start) {
                // allow bit of leeway, otherwise the stream is likely to hang
                camera_stream.video_element.currentTime = buffer_start + 30;
            };
        };

        camera_stream.video_element.onplay = function (e) {
            // If the video has been paused for long enough that the currentTime is now
            // earlier than the earliest video data in the buffer, this callback causes
            // the video to jump ahead to a valid position in the stream.
            let current_time = camera_stream.video_element.currentTime;
            let buffer_start = camera_stream.source_buffer.buffered.start(0);
            if (current_time < buffer_start) {
                camera_stream.video_element.currentTime = buffer_start + 30;
            };
        };

        camera_stream.video_element.onprogress = function (e) {
            // To avoid problems with the source_buffer becoming full, we need to manage
            // the amount of video data in the source_buffer manually. This callback runs
            // periodically, and limits the source_buffer to having a maximum of the most
            // recent 90 seconds of data
            console.log("progress")
            let source_buffer = camera_stream.source_buffer;
            let buff_time_range = source_buffer.buffered;
            if (buff_time_range.length > 0) {
                let buffer_start = buff_time_range.start(0);
                let buffer_end = buff_time_range.end(0)

                if (camera_stream.current_duration < buffer_end && buffer_end > 90) {
                    // we are at the start of a new group of fragments
                    camera_stream.current_duration = buffer_end;
                    if (!source_buffer.updating) {
                        source_buffer.remove(buffer_start, Math.max(buffer_start + 0.01, buffer_end - 90))
                    }
                }
            }
        }

        camera_stream.video_element.onerror = function (e) {
            console.log("Error!")
            console.log(e)
            camera_stream.close()
        }

        // set up the websocket which will give us all the data
        let ws = new WebSocket(`ws://${camera_stream.server_ip_address}:${camera_stream.server_port}/ws`);
        ws.binaryType = "arraybuffer";
        camera_stream.ws = ws;

        ws.onopen = function () {
            console.log("websocket open");
            // when we open the webscoket, let the server know which camera we are viewing
            ws.send(camera_stream.camera_id);
        };

        ws.onmessage = function (event) {
            // called when new data arrives in the websocket
            CameraStream.receiveFragment(camera_stream, event.data);
        };

        ws.onclose = function () {
            console.log("websocket close");
        };
    }

    static loadFragment(camera_stream) {
        // load the next video fragment to the media source buffer
        // called in response to the source_buffer "updateend" event
        let source_buffer = camera_stream.source_buffer;

        if (!source_buffer.updating) {
            let fragment_queue = camera_stream.fragment_queue;
            if (fragment_queue.length > 0) {
                let fragment = fragment_queue.shift(); // pop from the beginning
                source_buffer.appendBuffer(fragment);
            }
            else {
                // the queue is empty, so the next packet will be fed directly from the
                // websocket callback
                camera_stream.stream_started = false;
            }
        }
        else {
            // source_buffer was still updating; this branch shouldn't routinely run
            console.log("Not ready");
        }
    }

    static receiveFragment(camera_stream, fragment) {
        // receive the next video fragment from the websocket
        // called in response to the websocket "onmessage" event
        let source_buffer = camera_stream.source_buffer;
        camera_stream.f = camera_stream.f + 1

        // load the fragment directly into the source_buffer if the fragment_queue
        // is empty. Otherwise, append it to the fragment_queue where it will be loaded
        // into the source_buffer shortly
        if (!camera_stream.stream_started && !source_buffer.updating) {
            source_buffer.appendBuffer(fragment);
            camera_stream.stream_started = true;
        } else {
            camera_stream.fragment_queue.push(fragment);
            console.log("Fragment pushed to queue. Queue length:", camera_stream.fragment_queue.length);
        };
    }

    close() {
        this.ws.close();
        if (this.ms.readyState == "open") {
            if (!this.source_buffer.updating) {
                this.ms.endOfStream();
            } else {
                console.log("close() failed - source buffer is updating")
            };
        } else {
            console.log("close() failed - media source is not open")
        };
        delete CAMERA_STREAMS[this.camera_id];
    }
}

// here is the entrypoint for the dash clientside callback, which runs when the video element
// is loaded in the dom
window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        mse_client: function (_, camera_id, server_ip_address, server_port) {
            console.log("mse_client called")
            const targetNode = document.getElementById("active-output");
            // if (targetNode.value !== "livestream") {
            //     return;
            // };

            new CameraStream(camera_id, server_ip_address, server_port).init();

            // keep an eye out to see if the user changes output
            const config = { attributes: true, attributeOldValue: true }
            const callback = function (mutationsList, _) {
                for (const mutation of mutationsList) {
                    if (mutation.oldValue == "livestream" && mutation.target.value !== "livestream") {
                        // we've switched output, so stop the video stream
                        CAMERA_STREAMS[camera_id].close()
                    }
                }
            }

            const observer = new MutationObserver(callback);

            observer.observe(targetNode, config);
        },
        focus_form_field: function (modal_is_open, element_id) {
            if (!modal_is_open) {
                return;
            };

            let el = document.getElementById(element_id);
            el.focus();
        }
    }
})
