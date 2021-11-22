*** README

***** VIDEO

installed v4l2loopback-dkms

installed v4l2loopback-utils
- required reboot and "enroll MOK" thingy set on system startup



***** SOUND

using pulseaudio client `pactl`

create sink for the sound
`pactl load-module module-null-sink sink_name=effects-sink sink_properties=device.description=Effects-sink`

create loopback from real mic to the sink
`pactl load-module module-loopback source=alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source sink=effects-sink latency_msec=20`

create monitor to make source visible for apps
`pactl load-module module-remap-source master=effects-sink.monitor source_properties=device.description=Effects-mic`

unnecessary virtual mic???
`pactl load-module module-pipe-source source_name=effects-mic file=/dev/effects-mic format=s16le rate=16000 channels=1`

unnecessary mapping??
`pactl load-module module-combine-sink sink_name=effects-microphone-and-speakers slaves=effects-sink,@DEFAULT_SINK@`
