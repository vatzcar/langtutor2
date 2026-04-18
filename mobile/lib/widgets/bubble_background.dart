import 'dart:math';
import 'package:flutter/material.dart';

/// A decorative background that renders subtle semi-transparent bubbles
/// over a solid [backgroundColor], with [child] layered on top.
class BubbleBackground extends StatelessWidget {
  const BubbleBackground({
    super.key,
    required this.backgroundColor,
    required this.child,
  });

  final Color backgroundColor;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Solid color layer
        Positioned.fill(
          child: Container(color: backgroundColor),
        ),
        // Bubble decoration layer
        Positioned.fill(
          child: CustomPaint(
            painter: _BubblePainter(),
          ),
        ),
        // Content layer
        child,
      ],
    );
  }
}

class _BubblePainter extends CustomPainter {
  static const int _bubbleCount = 12;
  static const int _seed = 42;

  @override
  void paint(Canvas canvas, Size size) {
    final random = Random(_seed);

    for (int i = 0; i < _bubbleCount; i++) {
      final dx = random.nextDouble() * size.width;
      final dy = random.nextDouble() * size.height;
      final radius = 20.0 + random.nextDouble() * 80.0; // 20–100
      final opacity = 0.03 + random.nextDouble() * 0.06; // 0.03–0.09

      final paint = Paint()
        ..color = Colors.white.withValues(alpha: opacity)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(dx, dy), radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
