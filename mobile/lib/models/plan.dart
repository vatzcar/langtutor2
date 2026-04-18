class Plan {
  final String id;
  final String name;
  final String slug;
  final double priceMonthly;
  final double priceYearly;
  final int textLearningLimitMinutes;
  final int voiceCallLimitMinutes;
  final int videoCallLimitMinutes;
  final int agenticVoiceLimitMonthly;
  final int coordinatorVideoLimitMonthly;

  const Plan({
    required this.id,
    required this.name,
    required this.slug,
    required this.priceMonthly,
    required this.priceYearly,
    required this.textLearningLimitMinutes,
    required this.voiceCallLimitMinutes,
    required this.videoCallLimitMinutes,
    required this.agenticVoiceLimitMonthly,
    required this.coordinatorVideoLimitMonthly,
  });

  factory Plan.fromJson(Map<String, dynamic> json) {
    return Plan(
      id: json['id'] as String,
      name: json['name'] as String,
      slug: json['slug'] as String,
      priceMonthly: (json['price_monthly'] as num).toDouble(),
      priceYearly: (json['price_yearly'] as num).toDouble(),
      textLearningLimitMinutes: json['text_learning_limit_minutes'] as int,
      voiceCallLimitMinutes: json['voice_call_limit_minutes'] as int,
      videoCallLimitMinutes: json['video_call_limit_minutes'] as int,
      agenticVoiceLimitMonthly: json['agentic_voice_limit_monthly'] as int,
      coordinatorVideoLimitMonthly:
          json['coordinator_video_limit_monthly'] as int,
    );
  }

  bool get hasVoiceCall => voiceCallLimitMinutes > 0;

  bool get hasVideoCall => videoCallLimitMinutes > 0;

  bool get isUnlimitedVoice => voiceCallLimitMinutes == -1;

  bool get isUnlimitedVideo => videoCallLimitMinutes == -1;

  double get yearlySavings {
    final monthlyTotal = priceMonthly * 12;
    if (monthlyTotal == 0) return 0;
    return ((monthlyTotal - priceYearly) / monthlyTotal) * 100;
  }
}
