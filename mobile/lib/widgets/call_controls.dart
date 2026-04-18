import 'package:flutter/material.dart';

import '../config/theme.dart';

/// In-call control bar with video toggle, end-call, and voice toggle buttons.
class CallControls extends StatelessWidget {
  const CallControls({
    super.key,
    required this.isVideoCall,
    required this.videoEnabled,
    required this.voiceEnabled,
    this.onToggleVideo,
    this.onToggleVoice,
    required this.onEndCall,
  });

  /// Whether the current call is a video call.
  final bool isVideoCall;

  /// Whether the video option is currently enabled / available.
  final bool videoEnabled;

  /// Whether the voice option is currently enabled / available.
  final bool voiceEnabled;

  final VoidCallback? onToggleVideo;
  final VoidCallback? onToggleVoice;
  final VoidCallback onEndCall;

  @override
  Widget build(BuildContext context) {
    // Video button is disabled when video is off or already on a video call.
    final bool videoDisabled = !videoEnabled || isVideoCall;
    // Voice button is disabled when voice is off or already on a voice call.
    final bool voiceDisabled = !voiceEnabled || !isVideoCall;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Video toggle
        _ControlButton(
          icon: Icons.videocam_rounded,
          size: 52,
          bgColor: videoDisabled ? AppColors.disabledBg : AppColors.navBg,
          iconColor: videoDisabled ? AppColors.disabled : Colors.white,
          onTap: videoDisabled ? null : onToggleVideo,
        ),
        const SizedBox(width: 24),

        // End call
        _ControlButton(
          icon: Icons.call_end_rounded,
          size: 72,
          bgColor: AppColors.error,
          iconColor: Colors.white,
          onTap: onEndCall,
          elevation: 6,
        ),
        const SizedBox(width: 24),

        // Voice toggle
        _ControlButton(
          icon: Icons.mic_rounded,
          size: 52,
          bgColor: voiceDisabled ? AppColors.disabledBg : AppColors.navBg,
          iconColor: voiceDisabled ? AppColors.disabled : Colors.white,
          onTap: voiceDisabled ? null : onToggleVoice,
        ),
      ],
    );
  }
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.size,
    required this.bgColor,
    required this.iconColor,
    required this.onTap,
    this.elevation = 0,
  });

  final IconData icon;
  final double size;
  final Color bgColor;
  final Color iconColor;
  final VoidCallback? onTap;
  final double elevation;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: bgColor,
          shape: BoxShape.circle,
          boxShadow: elevation > 0
              ? [
                  BoxShadow(
                    color: bgColor.withValues(alpha: 0.4),
                    blurRadius: elevation * 2,
                    offset: Offset(0, elevation / 2),
                  ),
                ]
              : null,
        ),
        child: Icon(icon, color: iconColor, size: size * 0.45),
      ),
    );
  }
}
