"""One-parameter teaching calculation, not an LLM or a real business classifier."""
import math


def probability(weight, feature):
    return 1 / (1 + math.exp(-weight * feature))


def positive_loss(p):
    return -math.log(p)


def main():
    weight, feature, target, learning_rate = 0.0, 1.0, 1.0, 1.0
    before = probability(weight, feature)
    gradient = (before - target) * feature
    updated_weight = weight - learning_rate * gradient
    after = probability(updated_weight, feature)
    print(f"p_before: {before:.6f}")
    print(f"loss_before: {positive_loss(before):.6f}")
    print(f"weight_after_step: {updated_weight:.6f}")
    print(f"p_after_step: {after:.6f}")
    print(f"loss_after_step: {positive_loss(after):.6f}")
    # A new inference input changes the result, without another update step.
    other = probability(updated_weight, 2.0)
    print(f"inference_other_input: {other:.6f}")
    print(f"weight_after_inference: {updated_weight:.6f}")


if __name__ == "__main__":
    main()
