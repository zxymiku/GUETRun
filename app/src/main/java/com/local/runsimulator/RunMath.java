package com.local.runsimulator;

public final class RunMath {
    private RunMath() {}
    public static double positive(String value) {
        double n = Double.parseDouble(value.trim());
        if (!Double.isFinite(n) || n <= 0) throw new IllegalArgumentException("请输入大于 0 的数字");
        return n;
    }
    public static double pace(String value) {
        String[] parts = value.trim().replace('：', ':').split(":", -1);
        if (parts.length == 1) return positive(value) * 60;
        if (parts.length != 2 || !parts[0].matches("\\d+") || !parts[1].matches("\\d{1,2}"))
            throw new IllegalArgumentException("配速格式应为 6:00 或小数分钟");
        int seconds = Integer.parseInt(parts[1]);
        double total = Double.parseDouble(parts[0]) * 60 + seconds;
        if (seconds >= 60 || total <= 0) throw new IllegalArgumentException("配速秒数应在 0–59 之间");
        return total;
    }
    public static String duration(double seconds) {
        long s = Math.round(seconds);
        return String.format(java.util.Locale.ROOT, "%02d:%02d:%02d", s/3600, s/60%60, s%60);
    }
}
