import 'package:livekit_client/livekit_client.dart';

import '../config/constants.dart';

class LiveKitService {
  Room? _room;

  /// The current LiveKit room, if connected.
  Room? get room => _room;

  /// Connect to a LiveKit room with the given [token].
  Future<Room> connect(
    String token, {
    bool videoEnabled = true,
  }) async {
    _room = Room();

    await _room!.connect(
      AppConstants.liveKitUrl,
      token,
      roomOptions: const RoomOptions(
        adaptiveStream: true,
        dynacast: true,
      ),
    );

    // Enable microphone.
    await _room!.localParticipant?.setMicrophoneEnabled(true);

    // Enable camera if requested.
    await _room!.localParticipant?.setCameraEnabled(videoEnabled);

    // Use speakerphone by default.
    await Hardware.instance.setSpeakerphoneOn(true);

    return _room!;
  }

  /// Toggle the local camera on or off.
  Future<void> toggleVideo(bool enabled) async {
    await _room?.localParticipant?.setCameraEnabled(enabled);
  }

  /// Disconnect from the current room and release resources.
  Future<void> disconnect() async {
    await _room?.disconnect();
    await _room?.dispose();
    _room = null;
  }

  /// The first remote participant in the room, if any.
  RemoteParticipant? get remoteParticipant {
    final participants = _room?.remoteParticipants.values;
    if (participants == null || participants.isEmpty) return null;
    return participants.first;
  }
}
