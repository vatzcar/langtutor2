class Subscription {
  final String id;
  final String userId;
  final String planId;
  final String billingCycle;
  final String startedAt;
  final String? expiresAt;
  final bool isActive;

  const Subscription({
    required this.id,
    required this.userId,
    required this.planId,
    required this.billingCycle,
    required this.startedAt,
    this.expiresAt,
    this.isActive = true,
  });

  factory Subscription.fromJson(Map<String, dynamic> json) {
    return Subscription(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      planId: json['plan_id'] as String,
      billingCycle: json['billing_cycle'] as String,
      startedAt: json['started_at'] as String,
      expiresAt: json['expires_at'] as String?,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
