import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../config/theme.dart';

/// Circular avatar for a tutor persona with optional border and shadow.
class PersonaAvatar extends StatelessWidget {
  const PersonaAvatar({
    super.key,
    this.imageUrl,
    this.size = 200,
    this.showBorder = false,
  });

  /// Network URL for the persona image.
  final String? imageUrl;

  /// Diameter of the avatar.
  final double size;

  /// Whether to show a primary-coloured border ring.
  final bool showBorder;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: showBorder
            ? Border.all(color: AppColors.primary, width: 3)
            : null,
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.15),
            blurRadius: 20,
          ),
        ],
      ),
      child: ClipOval(
        child: _buildImage(),
      ),
    );
  }

  Widget _buildImage() {
    if (imageUrl != null && imageUrl!.isNotEmpty) {
      return CachedNetworkImage(
        imageUrl: imageUrl!,
        width: size,
        height: size,
        fit: BoxFit.cover,
        placeholder: (_, __) => _placeholder(),
        errorWidget: (_, __, ___) => _placeholder(),
      );
    }
    return _placeholder();
  }

  Widget _placeholder() {
    return Container(
      color: AppColors.disabledBg,
      child: Icon(
        Icons.person,
        size: size * 0.5,
        color: AppColors.disabled,
      ),
    );
  }
}
