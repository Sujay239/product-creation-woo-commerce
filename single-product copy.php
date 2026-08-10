/**
 * WooCommerce single product gallery:
 * Auto slide + infinite loop + bullet pagination + remove Previous/Next
 */
<?php
add_filter('woocommerce_single_product_carousel_options', function ($options) {

    $options['animation']       = 'slide';
    $options['animationLoop']   = true;   // infinite loop
    $options['slideshow']       = true;   // auto slide ON
    $options['slideshowSpeed']  = 3000;   // 3 seconds
    $options['animationSpeed']  = 600;
    $options['controlNav']      = true;   // bullets ON
    $options['directionNav']    = false;  // previous/next OFF
    $options['smoothHeight']    = true;
    $options['touch']           = true;
    $options['pauseOnHover']    = true;

    return $options;

}, 9999);


add_action('wp_head', function () {
    if (!is_product()) return;
    ?>
    <style>
        /* Hide thumbnail gallery */
        .single-product .woocommerce-product-gallery .flex-control-thumbs {
            display: none !important;
        }

        /* Remove Previous / Next text completely */
        .single-product .woocommerce-product-gallery .flex-direction-nav,
        .single-product .woocommerce-product-gallery .flex-direction-nav li,
        .single-product .woocommerce-product-gallery .flex-direction-nav a {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
        }

        /* Bullet pagination */
        .single-product .woocommerce-product-gallery .flex-control-paging {
            display: flex !important;
            justify-content: center;
            align-items: center;
            gap: 9px;
            list-style: none !important;
            margin: 14px 0 0 !important;
            padding: 0 !important;
        }

        .single-product .woocommerce-product-gallery .flex-control-paging li {
            margin: 0 !important;
            padding: 0 !important;
            list-style: none !important;
            width: auto !important;
        }

        .single-product .woocommerce-product-gallery .flex-control-paging li a {
            width: 8px !important;
            height: 8px !important;
            display: block !important;
            border-radius: 50% !important;
            background: #cfcfcf !important;
            border: none !important;
            font-size: 0 !important;
            text-indent: -9999px !important;
            overflow: hidden !important;
            cursor: pointer;
            transition: all 0.25s ease;
        }

        .single-product .woocommerce-product-gallery .flex-control-paging li a.flex-active {
            background: #111 !important;
            transform: scale(1.25);
        }

        @media (max-width: 767px) {
            .single-product .woocommerce-product-gallery .flex-control-paging {
                margin-top: 12px !important;
            }

            .single-product .woocommerce-product-gallery .flex-control-paging li a {
                width: 7px !important;
                height: 7px !important;
            }
        }
    </style>
    <?php
});